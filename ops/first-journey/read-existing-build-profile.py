#!/usr/bin/env python3
"""Read selected ACT build/routing facts. No app import, provider call or mutation.

Run with python3 -B. Configuration and route clues do not prove authorization,
the running application's loaded settings, or connected-journey readiness.
"""
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
from urllib.parse import urlsplit

EXPECTED = Path("/var/www/atg/front-end/releases/20261015-892317f")
RECEIPT = Path("/root/act-release-backup/cutover-dydysjlc/frontend-switch-892317f/activation-z9391_cw/ACTIVATED.json")
UNKNOWN = "UNKNOWN"


def emit(label, value):
    print(label + "=" + json.dumps(value, sort_keys=True))


def read_command(*args, env=None):
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, timeout=20, env=env)
        return result.stdout if result.returncode == 0 else None
    except (OSError, UnicodeError, subprocess.SubprocessError):
        return None


def safe_path(value):
    return value if isinstance(value, str) and re.fullmatch(r"/[A-Za-z0-9_./*-]{1,255}", value) and ".." not in Path(value).parts else UNKNOWN


def safe_name(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", value) else UNKNOWN


def origin(value):
    try:
        url = urlsplit(value)
        if (not re.fullmatch(r"https?://[^\s\\?#]+", value) or
                url.username or url.password or not url.hostname or url.query or url.fragment):
            return UNKNOWN
        _ = url.port
        return url.scheme + "://" + url.netloc
    except (TypeError, ValueError):
        return UNKNOWN


def build_facts(root):
    origins, quote_paths, modes, map_literals = set(), set(), set(), False
    expected_quotes = []
    files, size = 0, 0
    static = (root / ".next/static").resolve()
    for path in static.rglob("*.js"):
        files += 1
        size += path.stat().st_size
        if files > 1500 or size > 100_000_000 or not path.resolve().is_relative_to(static):
            return {"scan": UNKNOWN, "reason": "bounded scan could not cover all client JavaScript"}
        text = path.read_text()
        for value in re.findall(r"""["'](https?://[^"'\\\s]+/api/trips/calculate-trip-cost/)["']""", text):
            origins.add(origin(value))
            quote_paths.add("expected_root_api_path" if urlsplit(value).path == "/api/trips/calculate-trip-cost/" else "UNEXPECTED_PATH")
            expected_quotes.append(value == "https://airportandcitytransfer.com/api/trips/calculate-trip-cost/")
        modes.update(re.findall(r"""["']pk_(test|live)_[A-Za-z0-9_]{16,}["']""", text))
        map_literals |= bool(re.search(r"""googleMapsApiKey\s*:\s*["'][^"']+["']""", text))
    return {"scan": "complete" if files else UNKNOWN,
            "quote_api_literal_origins": sorted(origins) or UNKNOWN,
            "quote_literal_paths": sorted(quote_paths) or UNKNOWN,
            "all_quote_literals_equal_expected_act_endpoint": all(expected_quotes) if expected_quotes else UNKNOWN,
            "stripe_literal_modes": sorted(modes) or UNKNOWN,
            "maps_literal_present": map_literals, "js_files": files,
            "scope": "literal evidence only; does not prove the Stripe account or working provider access"}


NODE_PROBE = r"""
try {
  const root=process.argv[1], silent={info(){},warn(){},error(){}};
  const result=require(require.resolve('@next/env',{paths:[root]})).loadEnvConfig(root,false,silent,true);
  const e=result.combinedEnv, v=e.NEXT_PUBLIC_API_BASE_URL || '';
  let api='UNKNOWN', path='UNKNOWN';
  try { const u=new URL(v);
    if (/^https?:\/\/[^\s\\?#]+$/.test(v) && !u.username && !u.password) {
      api=u.origin; path=['/','/api','/api/'].includes(u.pathname)?u.pathname:'other';
    }
  } catch {}
  const key=e.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || '';
  const mode=/^pk_test_[A-Za-z0-9]+$/.test(key)?'test':/^pk_live_[A-Za-z0-9]+$/.test(key)?'LIVE':'UNKNOWN';
  process.stdout.write(JSON.stringify({api_origin:api,api_path:path,stripe_mode:mode,
    maps_api_key_present:!!e.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY,
    legacy_maps_key_present:!!e.NEXT_PUBLIC_GOOGLE_MAPS_KEY,
    loaded_files:result.loadedEnvFiles.map(f=>f.path).filter(p=>/^\.env(?:\.production)?(?:\.local)?$/.test(p))}));
} catch { process.stdout.write('{"resolution":"UNKNOWN"}'); }
"""


def environment_facts(root, node, process_env):
    selected = {k: v for k, v in process_env.items() if k.startswith("NEXT_PUBLIC_")}
    selected.update({"NODE_ENV": "production", "PATH": "/usr/bin:/bin"})
    indirect = False
    for name in (".env.production.local", ".env.local", ".env.production", ".env"):
        path = root / name
        if path.is_file():
            refs = set(re.findall(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", path.read_text()))
            indirect |= bool(refs.intersection(process_env).difference(selected))
    output = read_command(str(node), "-e", NODE_PROBE, str(root), env=selected)
    facts = json.loads(output) if output else {"resolution": UNKNOWN}
    facts["scope"] = "current production envfiles plus initial public process variables; not original build provenance"
    if indirect:
        facts = {"resolution": UNKNOWN, "reason": "envfiles reference excluded nonpublic process variables"}
    return facts


def pm2_facts(root, process_env, uid):
    owner = pwd.getpwuid(uid)
    home = process_env.get("PM2_HOME") or str(Path(owner.pw_dir) / ".pm2")
    facts = {"owner": safe_name(owner.pw_name), "uid": uid,
             "name": safe_name(process_env.get("name")), "id": safe_name(process_env.get("pm_id")),
             "home": safe_path(home), "cwd": safe_path(process_env.get("pm_cwd")),
             "script": safe_path(process_env.get("pm_exec_path")), "saved_matches": []}
    dump = Path(home) / "dump.pm2"
    if safe_path(home) != UNKNOWN and dump.is_file() and dump.stat().st_size <= 10_000_000:
        records = json.loads(dump.read_text())
        for record in records if isinstance(records, list) else []:
            row = record.get("pm2_env", record) if isinstance(record, dict) else {}
            if row.get("pm_cwd") == str(root):
                facts["saved_matches"].append({"name": safe_name(row.get("name")),
                    "script": safe_path(row.get("pm_exec_path")),
                    "autorestart": row.get("autorestart") if isinstance(row.get("autorestart"), bool) else UNKNOWN})
    facts["scope"] = "process identity and saved dump only; no PM2 command or daemon contact"
    return facts


TOKEN = re.compile(r"""\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[{};]|[^\s{};"'#]+""")


def parse_nginx(text):
    tokens = [m.group() for m in TOKEN.finditer(text) if not m.group().isspace() and not m.group().startswith("#")]
    stack, head = [[]], []
    for token in tokens:
        if token == "{":
            if not head:
                raise ValueError("unrecognised block")
            child = []
            stack[-1].append((head, child))
            stack.append(child)
            head = []
        elif token == ";":
            stack[-1].append((head, None))
            head = []
        elif token == "}":
            if head or len(stack) == 1:
                raise ValueError("unrecognised nesting")
            stack.pop()
        else:
            head.append(token[1:-1] if token[:1] in ("'", '"') else token)
    if head or len(stack) != 1:
        raise ValueError("incomplete configuration")
    return stack[0]


def safe_directives(nodes):
    result = []
    for words, children in nodes:
        if not words:
            continue
        name, args = words[0], words[1:]
        if name == "listen" and args:
            port = re.search(r"(?:^|:)(80|443)$", args[0])
            result.append([name, port[1] if port else UNKNOWN, "ssl" if "ssl" in args else "ssl_not_explicit"])
        elif name in ("auth_basic", "auth_request", "allow", "deny", "satisfy"):
            result.append([name, "off" if args == ["off"] else "present"])
        elif name == "proxy_pass" and len(args) == 1:
            value = args[0]
            if re.fullmatch(r"http://unix:/[A-Za-z0-9_./-]+(?::/[A-Za-z0-9_./-]*)?", value):
                result.append([name, value])
            else:
                api = origin(value)
                path = urlsplit(value).path if api != UNKNOWN else ""
                result.append([name, api + (path if path in ("", "/", "/api/", "/ws/", "/ws/trips/") else "/OTHER_PATH") if api != UNKNOWN else UNKNOWN])
        elif name in ("proxy_http_version", "proxy_read_timeout") and len(args) == 1:
            result.append([name, args[0] if re.fullmatch(r"[0-9.]+[smh]?", args[0]) else UNKNOWN])
        elif name == "proxy_set_header" and len(args) == 2 and args[0].lower() in ("upgrade", "connection"):
            value = args[1]
            result.append([name, args[0], value if re.fullmatch(r"\$[A-Za-z0-9_]+|upgrade|close|keep-alive", value) else UNKNOWN])
        elif name in ("include", "alias", "root") and len(args) == 1:
            result.append([name, safe_path(args[0])])
        elif name == "add_header" and args and args[0].lower() == "content-security-policy":
            result.append([name, "CSP_PRESENT; connect policy requires review"])
        elif children is not None and name != "location":
            result.append(["nested_block", safe_name(name), UNKNOWN])
    return result


def nginx_facts(text):
    if not text:
        return UNKNOWN
    results, blocks, references, upgrades = [], [], set(), []
    sections = re.split(r"(?m)^# configuration file ([^\n:]+):\n", text)
    for index in range(1, len(sections), 2):
        tree = parse_nginx(sections[index + 1])
        pending = list(tree)
        while pending:
            words, children = pending.pop()
            if children:
                pending.extend(children)
                blocks.append((words, children, sections[index]))
            if len(words) == 3 and words[:2] == ["map", "$http_upgrade"] and children:
                entries = []
                for w, c in children:
                    entries.append(w if c is None and len(w) == 2 and w[0] in ("default", "") and w[1] in ("upgrade", "close") else [UNKNOWN])
                upgrades.append({"variable": safe_name(words[2][1:]) if words[2].startswith("$") else UNKNOWN, "entries": entries})
            if words != ["server"] or not children:
                continue
            names = [w[1:] for w, c in children if w and w[0] == "server_name"]
            if not any("airportandcitytransfer.com" in row for row in names):
                continue
            locations = []
            for w, c in children:
                if c is not None and w and w[0] == "location" and any(
                        part == "/" or any(prefix in part for prefix in ("/api", "/ws", "/static", "/_next")) for part in w[1:]):
                    label = " ".join(w[1:])
                    locations.append({"location": label if re.fullmatch(r"[A-Za-z0-9_./~*^= -]{1,160}", label) else UNKNOWN,
                                      "directives": safe_directives(c)})
                    for directive, nested in c:
                        if len(directive) == 2 and directive[0] == "proxy_pass" and origin(directive[1]) != UNKNOWN:
                            references.add(urlsplit(directive[1]).hostname)
            results.append({"file": safe_path(sections[index]), "server_directives": safe_directives(children), "locations": locations})
    upstreams = []
    for words, children, filename in blocks:
        if len(words) == 2 and words[0] == "upstream" and words[1] in references:
            endpoints = []
            for w, c in children:
                if len(w) >= 2 and w[0] == "server":
                    value = w[1]
                    endpoints.append("unix:" + safe_path(value[5:]) if value.startswith("unix:") else
                                     value if re.fullmatch(r"[A-Za-z0-9_.:\[\]-]{1,160}", value) else UNKNOWN)
            upstreams.append({"name": safe_name(words[1]), "file": safe_path(filename), "endpoints": endpoints or UNKNOWN})
    return {"explicit_act_blocks": results or UNKNOWN,
            "referenced_upstreams": upstreams, "http_upgrade_maps": upgrades,
            "scope": "explicit directives only; unresolved includes, complex rules and inheritance remain UNKNOWN",
            "viewer_authorization": "UNVERIFIED"}


def receipt_facts():
    if not RECEIPT.is_file() or RECEIPT.stat().st_size > 200_000:
        return UNKNOWN
    data, selected = json.loads(RECEIPT.read_text()), {}
    def visit(value, key="", depth=0):
        if depth > 5 or len(selected) >= 40:
            return
        if isinstance(value, dict):
            for k, v in value.items():
                if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", str(k)):
                    visit(v, key + "." + str(k), depth + 1)
        elif key.rsplit(".", 1)[-1] in ("git_sha", "source_sha", "frontend_sha", "backend_sha", "commit_sha", "candidate_sha", "previous_sha", "accepted_sha") and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value):
            selected[key] = value
        elif key.rsplit(".", 1)[-1] in ("frontend_release", "candidate_dir", "new_release", "release_dir", "nginx_config", "nginx_path", "nginx_backup", "static_union", "static_union_path", "activation_dir", "receipt_path", "pm2_dump", "pm2_dump_backup", "previous_release", "previous_frontend_release", "source_root", "frontend_root") and isinstance(value, str) and value.startswith(("/var/www/atg/front-end/", "/etc/nginx/", "/root/act-release-backup/", "/home/act/.pm2/")):
            selected[key] = safe_path(value)
        elif key.rsplit(".", 1)[-1] in ("port", "frontend_port", "old_port", "new_port", "pid") and type(value) is int:
            selected[key] = value if 0 <= value <= 10_000_000 else UNKNOWN
    visit(data)
    return {"keys": [k for k in data if re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", k)] if isinstance(data, dict) else UNKNOWN,
            "selected": selected}


def main():
    listeners = read_command("ss", "-H", "-ltnp", "( sport = :3002 )")
    pids = sorted(set(re.findall(r"pid=(\d+)", listeners or "")))
    if len(pids) != 1:
        raise SystemExit("INSPECTION=UNKNOWN: exactly one port-3002 process was not identified; no changes made.")
    proc = Path("/proc") / pids[0]
    root, node = (proc / "cwd").resolve(), (proc / "exe").resolve()
    if root != EXPECTED:
        raise SystemExit("INSPECTION=UNKNOWN: serving release differs from expected 892317f; no changes made.")
    process_env = dict(item.split("=", 1) for item in (proc / "environ").read_text().split("\0") if "=" in item)
    uid = int(re.search(r"(?m)^Uid:\s+(\d+)", (proc / "status").read_text())[1])
    emit("SERVING_FRONTEND", {"pid": int(pids[0]), "path": str(root), "node": safe_path(str(node))})
    for label, action in (
            ("CLIENT_BUILD", lambda: build_facts(root)),
            ("CURRENT_CONFIG", lambda: environment_facts(root, node, process_env)),
            ("PM2_IDENTITY", lambda: pm2_facts(root, process_env, uid)),
            ("NGINX_ROUTING", lambda: nginx_facts(read_command("nginx", "-T"))),
            ("PREVIOUS_ACTIVATION", receipt_facts)):
        try:
            emit(label, action())
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
            emit(label, UNKNOWN)
    spare = read_command("ss", "-H", "-ltn", "( sport = :3003 )")
    emit("PORT_3003", UNKNOWN if spare is None else "occupied" if spare.strip() else "available_at_inspection")
    print("READ_ONLY_COMPLETE: no settings or services changed; authorization and journey readiness unverified.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        raise SystemExit("INSPECTION=UNKNOWN: inspection incomplete; no changes made.")
