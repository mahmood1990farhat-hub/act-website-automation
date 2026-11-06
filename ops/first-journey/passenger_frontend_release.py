#!/usr/bin/env python3
"""Prepare an inactive ACT passenger-page release; activate only after approval.

The only permitted application change is MyTripsCard.tsx, plus its focused test.
The existing 3a82c16 frontend remains the rollback on 3003. Backend d77e896 is
read-only throughout. No migration, booking, payment, GPS or customer request.
Prepare: --prepare --frontend-sha <reviewed full SHA>
Activate: --activate --frontend-sha <same SHA> --record <prepared private record>
Retry the recorded rollback once: add --retry-after-rollback (eoszulb3 only).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
import argparse
import copy
import fcntl
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import secrets
import shutil
import signal
import stat
import subprocess
import tarfile
import tempfile
import time
from urllib.parse import quote, urlsplit

OLD_SHA = "3a82c16f1eb648f274759b2567db4fe433720d17"
REVIEWED_SHA = "02e59f95b5fd85d6ad07e881f3f2671a01a7bd65"
REVIEWED_FILES = {
    "src/components/_components/Trips/MyTripsCard.tsx": "cfa7b6ab379acfa85af95c45295b14d6d0285ee436627cc601dddc57bad43892",
    "tests/passenger-trip-details.cjs": "9a2f524acc6107bef5caddcdc3789ca51041cfc8146fabef2ac48f213245ea67",
}
BACK_SHA = "d77e896af9daca5a39b7a85d5b76c5821e008d23"
CONSUMER_HASH = "d10d943b079041e0998daae2e4ece3a90c1b125f64107ef4676c1d51d9c55bed"
FRONT_ROOT = Path("/var/www/atg/front-end")
OLD_FRONT = FRONT_ROOT / "releases/20261106-tracking-3a82c16-oe9oh1vi"
OLD_ASSETS = FRONT_ROOT / "act-static-tracking-3a82c16-oe9oh1vi"
BACK_ROOT = Path("/var/www/atg/atg-backend")
BACK_FRONT = BACK_ROOT / "releases/20261106-tracking-d77e896-oe9oh1vi/backend"
BACKUP = Path("/root/act-release-backup")
PRIOR = BACKUP / "tracking-stage-oe9oh1vi"
PRIOR_ACTIVATION = PRIOR / "activation-spxsopb7/ACTIVATED.json"
REPO = FRONT_ROOT / "airportandcitytransfer_repo"
SITE = Path("/etc/nginx/sites-enabled/airportandcitytransfer")
MASTER = Path("/etc/nginx/nginx.conf")
NODE_DIR = Path("/home/act/.nvm/versions/node/v24.13.0/bin")
NODE, NPM = NODE_DIR / "node", NODE_DIR / "npm"
PM2_ROOT = NODE_DIR.parent / "lib/node_modules/pm2"
PM2_HOME = Path("/home/act/.pm2")
DUMP = PM2_HOME / "dump.pm2"
DOMAIN = "airportandcitytransfer.com"
ORIGIN = "https://" + DOMAIN
RETAINED = ("act", "act-preview-892317f", "act-tracking-3a82c16")
ENV_FILES = (".env.production.local", ".env.local", ".env.production", ".env")
ALLOWED = {"src/components/_components/Trips/MyTripsCard.tsx", "tests/passenger-trip-details.cjs"}
POLICY = {"autorestart": True, "restart_delay": 3000, "max_restarts": 5, "min_uptime": 10000}
ARGS = ["start", "--hostname", "127.0.0.1", "--port", "3004"]
LAUNCH = ("pm_cwd", "pm_exec_path", "exec_interpreter", "args", "exec_mode", "env", *POLICY)
IDENTITY = (*LAUNCH, "status", "restart_time", "pm_uptime")
SYSTEM_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}


class Stop(Exception):
    """Only fixed, safe-to-print operator messages belong in this exception."""


def require(value, message):
    if not value:
        raise Stop(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def regular(path):
    require(path.is_file() and not path.is_symlink(), "Required regular file is missing or symlinked.")
    return path.read_bytes()


def private(path):
    info = path.lstat()
    require(path.resolve(strict=True) == path and info.st_uid == 0 and not info.st_mode & 0o077,
            "Release record must be an existing root-private path without symlinks.")


def write_new(path, data, mode=0o600):
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_file(path, data, expected):
    """Reviewed atomic replacement: preserve owner/mode/xattrs and refuse drift."""
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and sha(regular(path)) == expected,
            "File preimage changed; overwrite refused.")
    descriptor, name = tempfile.mkstemp(prefix=".act-passenger-", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            os.fchown(stream.fileno(), info.st_uid, info.st_gid)
            os.fchmod(stream.fileno(), stat.S_IMODE(info.st_mode))
            stream.flush()
            os.fsync(stream.fileno())
        for key in os.listxattr(path, follow_symlinks=False):
            os.setxattr(temp, key, os.getxattr(path, key, follow_symlinks=False))
        now = path.lstat()
        require((now.st_dev, now.st_ino, now.st_mtime_ns, now.st_uid, now.st_gid, now.st_mode) ==
                (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_uid, info.st_gid, info.st_mode)
                and sha(regular(path)) == expected, "Concurrent file edit; overwrite refused.")
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temp.unlink(missing_ok=True)


def act_env():
    return {**SYSTEM_ENV, "HOME": "/home/act", "USER": "act", "LOGNAME": "act",
            "PM2_HOME": str(PM2_HOME), "PATH": str(NODE_DIR) + ":/usr/bin:/bin",
            "NODE_ENV": "production", "NEXT_TELEMETRY_DISABLED": "1",
            "PM2_PROGRAMMATIC": "1", "PM2_NO_INTERACTION": "true"}


def one(rows, name):
    matches = [row for row in rows if row.get("name") == name]
    require(len(matches) == 1, "A required PM2 definition is missing or duplicated.")
    return matches[0]


def identity(row):
    return {"name": row["name"], "pm_id": row["pm_id"], "pid": row["pid"],
            **{key: row["pm2_env"].get(key) for key in IDENTITY}}


def route_pair(original, assets):
    text = original.decode()
    ports = re.compile(r"(?m)^([ \t]*proxy_pass[ \t]+)http://127\.0\.0\.1:3003([ \t]*;)")
    alias = re.compile(r"(?m)^([ \t]*alias[ \t]+)" + re.escape(str(OLD_ASSETS)) + r"/([ \t]*;)")
    require(len(ports.findall(text)) == 3 and len(alias.findall(text)) == 1,
            "Expected exactly three current frontend upstreams and one current static alias.")
    rollback = alias.sub(lambda m: m[1] + str(assets) + "/" + m[2], text)
    return ports.sub(lambda m: m[1] + "http://127.0.0.1:3004" + m[2], rollback).encode(), rollback.encode()


def validation_master(master, entries, candidate):
    text = master.decode()
    include = re.compile(r"(?m)^[ \t]*include[ \t]+/etc/nginx/sites-enabled/\*[ \t]*;")
    require(len(include.findall(text)) == 1 and entries.count(SITE) == 1, "Unexpected Nginx include arrangement.")
    paths = [str(candidate if entry == SITE else entry) for entry in entries]
    require(all(not any(char in path for char in ('"', "\\", "\n", "\r", "$")) for path in paths),
            "Unsafe Nginx include path.")
    text = include.sub(lambda _: "\n".join('    include "' + path + '";' for path in paths), text)
    pid = re.compile(r"(?m)^[ \t]*pid[ \t]+[^;\n]+;")
    require(len(pid.findall(text)) <= 1, "Unexpected Nginx PID arrangement.")
    value = 'pid "' + str(candidate.parent / "nginx-validation.pid") + '";'
    return (pid.sub(lambda _: value, text) if pid.search(text) else value + "\n" + text).encode()


def tree(root, excluded=()):
    require(root.is_dir() and root.resolve(strict=True) == root, "Expected immutable directory is missing or symlinked.")
    result = {}
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            require(not (Path(current) / name).is_symlink(), "Links are forbidden in release or public asset trees.")
        if Path(current) == root:
            directories[:] = [name for name in directories if name not in excluded]
        for name in files:
            path = Path(current) / name
            result[str(path.relative_to(root))] = sha(regular(path))
    require(result, "Expected release or asset tree is empty.")
    return dict(sorted(result.items()))


def copy_assets(roots, destination):
    require(not destination.exists() and not destination.is_symlink(), "Asset destination already exists; preserved.")
    destination.mkdir(mode=0o755)
    destination.chmod(0o755)
    result = {}
    for root in roots:
        for relative, digest in tree(root).items():
            require(relative not in result or result[relative] == digest, "Public asset hash collision; staging refused.")
            if relative not in result:
                target = destination / relative
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                target.parent.chmod(0o755)
                write_new(target, regular(root / relative), 0o644)
                require(sha(regular(target)) == digest, "Public asset changed while copying.")
                result[relative] = digest
    # parents=True is affected by the deliberately private process umask.
    for current, _, _ in os.walk(destination):
        Path(current).chmod(0o755)
    return dict(sorted(result.items()))


PM2_READ = r'''
const fs=require('fs'),path=require('path'),root=process.argv[1],socket=process.argv[2];
function dep(n){const p=path.join(root,'modules',n);return fs.existsSync(p)?require(p):require(require.resolve(n,{paths:[root]}));}
const req=dep('pm2-axon').socket('req'),rpc=new (dep('pm2-axon-rpc').Client)(req);
const timer=setTimeout(()=>process.exit(2),15000);req.once('error',()=>process.exit(2));
req.once('connect',()=>rpc.call('getMonitorData',{},(e,r)=>{if(e||!Array.isArray(r))return process.exit(2);
 clearTimeout(timer);req.close();process.stdout.write(JSON.stringify(r),()=>process.exit(0));}));req.connect(socket);
'''
PM2_START = r'''
'use strict';
const fs=require('fs'),util=require('util'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const check=ok=>{if(!ok)throw new Error('PM2 activation guard refused');},same=util.isDeepStrictEqual;
console.log=(...args)=>process.stderr.write(args.join(' ')+'\n');
const pm2=require(process.argv[1]),c=JSON.parse(JSON.stringify(input.config)),timer=setTimeout(()=>process.exit(2),25000);
const call=(o,m,...a)=>new Promise((resolve,reject)=>o[m](...a,(e,r)=>e?reject(e):resolve(r)));
const id=p=>({name:p.name,pm_id:p.pm_id,pid:p.pid,...Object.fromEntries(input.identity_fields.map(k=>[k,p.pm2_env[k]??null]))});
const guard=r=>check(r.length===input.retained.length&&r.every(p=>input.retained.some(w=>same(id(p),w))));
const fail=cb=>{if(typeof cb==='function')cb(new Error('Daemon creation forbidden'));else throw new Error('Daemon creation forbidden');};
(async()=>{
 check(fs.lstatSync(input.socket).isSocket()&&Number(fs.readFileSync(input.pid_file,'utf8'))===input.daemon_pid);process.kill(input.daemon_pid,0);
 check(pm2.Client&&typeof pm2.Client.launchRPC==='function');pm2.Client.start=fail;pm2.Client.launchDaemon=fail;
 const execute=pm2.Client.executeRemote.bind(pm2.Client);
 pm2.Client.executeRemote=(method,data,cb)=>{
  if(method==='getMonitorData')return execute(method,data,cb);
  if(method!=='prepare')return cb(new Error('Unapproved PM2 method'));
  if(data.name!==c.name||data.pm_cwd!==c.cwd||data.pm_exec_path!==c.script||data.exec_interpreter!==c.interpreter||
   !same(data.args,c.args)||data.exec_mode!=='fork_mode'||data.instances!==1||!Object.entries(input.policy).every(([k,v])=>data[k]===v)||
   !Object.entries(c.env).every(([k,v])=>data.env?.[k]===v))return cb(new Error('Launch definition differs'));
  execute('getMonitorData',{},(e,r)=>{if(e)return cb(e);try{guard(r);}catch(error){return cb(error);}execute('prepare',data,cb);});};
 await call(pm2.Client,'launchRPC');guard(await call(pm2,'list'));await call(pm2,'start',{apps:[JSON.parse(JSON.stringify(c))]});
 const rows=await call(pm2,'list');check(rows.length===input.retained.length+1);
 for(const old of input.retained)check(rows.some(p=>same(id(p),old)));check(rows.filter(p=>p.name===c.name).length===1);
})().then(()=>{clearTimeout(timer);pm2.disconnect(()=>process.exit(0));}).catch(()=>{
 clearTimeout(timer);process.stderr.write('Candidate startup refused or incomplete.\n');pm2.disconnect(()=>process.exit(2));});
'''
PM2_REMOVE = r'''
'use strict';
const fs=require('fs'),path=require('path'),util=require('util'),root=process.argv[1],i=JSON.parse(fs.readFileSync(0,'utf8'));
function dep(n){const p=path.join(root,'modules',n);return fs.existsSync(p)?require(p):require(require.resolve(n,{paths:[root]}));}
const req=dep('pm2-axon').socket('req'),rpc=new (dep('pm2-axon-rpc').Client)(req),same=util.isDeepStrictEqual;
const timer=setTimeout(()=>process.exit(2),25000),done=c=>{clearTimeout(timer);req.close();process.exit(c);};
const id=p=>({name:p.name,pm_id:p.pm_id,pid:p.pid,...Object.fromEntries(i.identity_fields.map(k=>[k,p.pm2_env[k]??null]))});
req.once('error',()=>done(2));req.once('connect',()=>rpc.call('getMonitorData',{},(error,rows)=>{
 if(error||!Array.isArray(rows)||!i.retained.every(w=>rows.some(p=>same(id(p),w))))return done(2);
 const found=rows.filter(p=>p.name===i.name);
 if(found.length===0&&rows.length===i.retained.length)return done(i.allow_absent?0:2);
 if(found.length!==1||rows.length!==i.retained.length+1)return done(2);
 const p=found[0],e=p.pm2_env;
 if(e.pm_cwd!==i.cwd||e.pm_exec_path!==i.script||e.exec_interpreter!==i.interpreter||!same(e.args,i.args)||
  e.env?.ACT_TRACKING_ACTIVATION!==i.activation_nonce)return done(2);
 rpc.call('deleteProcessId',p.pm_id,e=>done(e?2:0));}));req.connect(i.socket);
'''
ENV_READ = r'''
const root=process.argv[1],silent={info(){},warn(){},error(){}};
const e=require(require.resolve('@next/env',{paths:[root]})).loadEnvConfig(root,false,silent,true).combinedEnv;
process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(e).filter(([k,v])=>k.startsWith('NEXT_PUBLIC_')&&typeof v==='string'))));
'''


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs if tag in ("script", "link") else ():
            if key in ("src", "href") and value:
                parsed = urlsplit(value)
                if not parsed.netloc and not parsed.query and parsed.path.startswith("/_next/static/"):
                    self.paths.add(parsed.path)


def html_assets(body):
    parser = Assets()
    parser.feed(body.decode("utf-8", "replace"))
    return parser.paths


def cache_metadata(raw):
    """Return only bounded cache hints, never arbitrary headers or cookies."""
    result = {}
    flags = {"public", "private", "no-cache", "no-store", "must-revalidate", "proxy-revalidate", "immutable", "no-transform"}
    for line in raw.decode("ascii", "replace").splitlines():
        name, separator, value = line.partition(":")
        name, value = name.lower(), value.strip()
        if not separator:
            continue
        if name == "age" and re.fullmatch(r"[0-9]{1,12}", value):
            result[name] = int(value)
        elif name == "cf-cache-status" and value in {"HIT", "MISS", "DYNAMIC", "EXPIRED", "STALE", "BYPASS", "REVALIDATED", "UPDATING", "NONE", "UNKNOWN"}:
            result[name] = value
        elif name == "x-nextjs-cache" and value in {"HIT", "MISS", "STALE", "REVALIDATED"}:
            result[name] = value
        elif name == "cache-control":
            directives = [item.strip().lower() for item in value[:512].split(",")]
            safe = [item for item in directives if item in flags or re.fullmatch(r"(?:max-age|s-maxage|stale-while-revalidate|stale-if-error)=[0-9]{1,12}", item)]
            if safe:
                result[name] = ", ".join(safe)
    return result


class Release:
    def __init__(self, revision, record=None, retry_after_rollback=False):
        self.revision, self.record, self.work = revision, record, None
        self.retry_after_rollback = retry_after_rollback
        self.phase, self.sequence = "preflight", 0
        self.start_attempted = self.start_acknowledged = self.dump_attempted = False
        self.route_attempted = self.reload_attempted = self.complete = False

    def journal(self, state):
        write_new(self.work / (state + ".json"), encoded({"state": state, "phase": self.phase,
                  "frontend_sha": self.revision, "backend_sha": BACK_SHA, "backend_changed": False,
                  "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "journey_accepted": False}))

    def command(self, label, args, *, env=None, cwd=None, data=None, timeout=30, log=False):
        process = subprocess.Popen([str(arg) for arg in args], cwd=cwd, env=env or SYSTEM_ENV,
                    stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            out, err = process.communicate(input=data, timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise Stop(label + " interrupted or exceeded its deadline.") from None
        if log:
            self.sequence += 1
            write_new(self.work / f"{self.sequence:02d}-{label}.log", out + err)
        require(process.returncode == 0, label + " failed; diagnostics remain private.")
        return out

    def git(self, *args):
        return self.command("source-operation", ["/usr/bin/git", "-C", REPO, *args],
                            env=os.environ.copy() | {"GIT_TERMINAL_PROMPT": "0"}, timeout=120)

    def backend(self):
        current = BACK_ROOT / "current"
        require(current.is_symlink() and current.resolve(strict=True) == BACK_FRONT,
                "The active d77e896 backend pointer changed; no backend action is permitted.")
        require(json.loads(regular(BACK_FRONT / "release.json")).get("git_sha") == BACK_SHA
                and sha(regular(BACK_FRONT / "apps/trips/consumers.py")) == CONSUMER_HASH,
                "The active backend receipt or source changed.")
        raw = self.command("backend-identity", ["/usr/bin/systemctl", "show", "act.service", "--no-pager",
                           "-p", "ActiveState", "-p", "MainPID"])
        values = dict(line.split("=", 1) for line in raw.decode().splitlines() if "=" in line)
        pid = int(values.get("MainPID", "0"))
        require(values.get("ActiveState") == "active" and pid > 1
                and Path(f"/proc/{pid}/cwd").resolve(strict=True) == BACK_FRONT, "Backend running identity differs.")
        return {"pid": pid, "pointer": os.readlink(current), "source": CONSUMER_HASH,
                "environment_hash": sha(regular(BACK_ROOT / "shared/.env"))}

    def rows(self):
        require((PM2_HOME / "rpc.sock").is_socket(), "Existing PM2 daemon socket is missing.")
        pid = int(regular(PM2_HOME / "pm2.pid").strip())
        require(pid > 1, "Invalid PM2 daemon identity.")
        os.kill(pid, 0)
        if hasattr(self, "daemon"):
            require(self.daemon == pid, "PM2 daemon changed during this release.")
        self.daemon = pid
        return json.loads(self.command("pm2-read", ["/usr/sbin/runuser", "-u", "act", "--", NODE,
                          "-e", PM2_READ, PM2_ROOT, PM2_HOME / "rpc.sock"], env=act_env(), timeout=20))

    def retained(self, rows, candidate=False):
        require(len(rows) == 3 + int(candidate), "PM2 inventory drifted; other processes are preserved.")
        for expected in self.baseline["retained"]:
            row = one(rows, expected["name"])
            require(identity(row) == expected and Path(f'/proc/{row["pid"]}/cwd').resolve(strict=True) == Path(expected["pm_cwd"]),
                    "A retained frontend changed during this release.")

    def other_nginx(self):
        effective = self.command("nginx-effective", ["/usr/sbin/nginx", "-T"])
        parts = re.split(rb"(?m)^# configuration file (.+):\n", effective)
        seen = 0
        for index in range(1, len(parts), 2):
            if parts[index].decode() in (str(SITE), str(self.site)):
                seen += 1
                parts[index + 1] = b"ACT_SITE_CHECKED_SEPARATELY\n"
        require(seen == 1, "Nginx does not include the expected ACT site exactly once.")
        return sha(b"\0".join(parts))

    def invariants(self, site_hash):
        require(self.backend() == self.baseline["backend"], "Backend identity changed; no backend action is permitted.")
        require(SITE.resolve(strict=True) == self.site and sha(regular(self.site)) == site_hash
                and sha(regular(MASTER)) == self.baseline["master_hash"]
                and [str(path) for path in sorted(SITE.parent.iterdir())] == self.baseline["entries"]
                and self.other_nginx() == self.baseline["other_nginx_hash"], "Nginx configuration drifted; overwrite refused.")

    def public_environment(self, rows):
        values = json.loads(regular(PRIOR / "frontend-public-environment.json"))
        require(isinstance(values, dict) and all(re.fullmatch(r"NEXT_PUBLIC_[A-Z0-9_]+", key) and isinstance(value, str)
                for key, value in values.items()), "Captured public configuration is malformed.")
        require(values.get("NEXT_PUBLIC_API_BASE_URL") == ORIGIN
                and re.fullmatch(r"pk_test_[A-Za-z0-9]{16,}", values.get("NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", "")),
                "Existing API origin or test-mode public payment configuration differs.")
        maps = values.get("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "")
        require(maps.strip() and not re.search(r"placeholder|synthetic|replace|your[_ -]?key", maps, re.I), "Existing Maps key is missing.")
        settings = one(rows, RETAINED[-1])["pm2_env"]
        overrides = {key: value for source in (settings, settings.get("env", {})) for key, value in source.items()
                     if key.startswith("NEXT_PUBLIC_") and isinstance(value, str)}
        resolved = json.loads(self.command("public-configuration", [NODE, "-e", ENV_READ, OLD_FRONT], env=act_env() | overrides))
        require(resolved == values, "Current build configuration differs from the prior captured configuration.")
        return values

    def capture_baseline(self):
        private(PRIOR)
        private(PRIOR_ACTIVATION.parent)
        prior = json.loads(regular(PRIOR / "plan.json"))
        receipt = json.loads(regular(PRIOR_ACTIVATION))
        require(receipt.get("state") == "ACTIVATED" and receipt.get("backend_sha") == BACK_SHA
                and receipt.get("frontend_sha") == OLD_SHA and prior.get("frontend_sha") == OLD_SHA
                and prior.get("backend_sha") == BACK_SHA and prior.get("frontend_release") == str(OLD_FRONT)
                and prior.get("backend_release") == str(BACK_FRONT) and prior.get("public_assets") == str(OLD_ASSETS),
                "The pinned prior tracking activation record differs.")
        expected_site = prior.get("candidate_sha256")
        if self.retry_after_rollback:
            require(self.record == BACKUP / "passenger-stage-eoszulb3"
                    and sha(self.original) == expected_site,
                    "Retry provenance does not match the original tracking routing.")
            expected_site = sha(self.rollback)
        self.site = SITE.resolve(strict=True)
        require(str(self.site) == prior.get("live_site_resolved") and self.site.is_relative_to(Path("/etc/nginx"))
                and sha(regular(self.site)) == expected_site
                and regular(OLD_FRONT / ".next/BUILD_ID").decode().strip() == prior.get("frontend_build_id"),
                "Current frontend routing or build differs from the activated 3a82c16 release.")
        old_manifest = regular(PRIOR / "assets-manifest.json")
        require(sha(old_manifest) == prior.get("asset_manifest_sha256") and tree(OLD_ASSETS) == json.loads(old_manifest),
                "Current public asset union differs from its prior manifest.")
        rows, dump = self.rows(), regular(DUMP)
        require({row.get("name") for row in rows} == set(RETAINED) and len(rows) == 3, "Expected three retained PM2 processes.")
        saved = json.loads(dump)
        require(isinstance(saved, list) and len(saved) == 3, "Saved PM2 process inventory differs.")
        for row in rows:
            require(row["pid"] > 1 and row["pm2_env"].get("status") == "online", "A retained frontend is not online.")
            disk = one(saved, row["name"])
            require(all(disk.get(key) == row["pm2_env"].get(key) for key in LAUNCH), "Saved/live PM2 definitions differ.")
        old = one(rows, RETAINED[-1])["pm2_env"]
        require(old.get("pm_cwd") == str(OLD_FRONT) and old.get("pm_exec_path") == str(OLD_FRONT / "node_modules/next/dist/bin/next")
                and old.get("exec_interpreter") == str(NODE) and old.get("args") == ARGS[:-1] + ["3003"], "Current frontend launch differs.")
        self.public = self.public_environment(rows)
        self.baseline = {"backend": self.backend(), "retained": [identity(one(rows, name)) for name in RETAINED],
            "daemon": self.daemon, "dump_hash": sha(dump), "master_hash": sha(regular(MASTER)),
            "entries": [str(path) for path in sorted(SITE.parent.iterdir())], "other_nginx_hash": self.other_nginx(),
            "old_site_hash": sha(regular(self.site)), "old_build_id": regular(OLD_FRONT / ".next/BUILD_ID").decode().strip(),
            "prior_plan_hash": sha(regular(PRIOR / "plan.json")),
            "prior_receipt_hash": sha(regular(PRIOR_ACTIVATION)),
            "env_hashes": {name: sha(regular(OLD_FRONT / name)) for name in ENV_FILES if (OLD_FRONT / name).exists()}}
        self.retained(rows)

    def require_source(self, fetch=False):
        require(self.revision == REVIEWED_SHA, "This helper only supports the exact reviewed passenger-page correction.")
        remote = self.git("remote", "get-url", "origin").decode().strip()
        parsed = urlsplit(remote)
        valid = remote in ("git@github.com:mahmood1990farhat-hub/act-website-automation.git", "git@github.com:mahmood1990farhat-hub/act-website-automation")
        valid |= parsed.scheme in ("ssh", "https") and parsed.hostname == "github.com" and not parsed.query and not parsed.fragment and parsed.path.strip("/").removesuffix(".git") == "mahmood1990farhat-hub/act-website-automation"
        require(valid, "Existing Git remote is not the expected ACT repository.")
        if fetch:
            self.git("fetch", "--no-write-fetch-head", "--no-tags", "origin", self.revision)
        require(self.git("rev-parse", self.revision + "^{commit}").decode().strip() == self.revision, "Candidate Git identity differs.")
        self.git("merge-base", "--is-ancestor", OLD_SHA, self.revision)
        changed = self.git("diff", "--name-only", OLD_SHA, self.revision, "--", "act_website-main").decode().splitlines()
        require({path.removeprefix("act_website-main/") for path in changed} == ALLOWED,
                "Candidate frontend changes exceed the reviewed passenger-page fix and its test.")
        require(not self.git("diff", "--name-only", "--diff-filter=D", OLD_SHA, self.revision, "--", "act_website-main").strip(),
                "Candidate deletes a reviewed frontend file.")
        for path, expected in REVIEWED_FILES.items():
            require(sha(self.git("show", self.revision + ":act_website-main/" + path)) == expected,
                    "Candidate passenger-page source differs from the reviewed content.")

    def environment_files_unchanged(self):
        for root in (OLD_FRONT, self.front):
            observed = {name: sha(regular(root / name)) for name in ENV_FILES if (root / name).exists()}
            require(observed == self.baseline["env_hashes"], "Current or candidate runtime environment files changed.")

    def paths(self):
        require(self.record.parent == BACKUP and re.fullmatch(r"passenger-stage-[a-z0-9_]+", self.record.name), "Unexpected staging record path.")
        tag = self.record.name.removeprefix("passenger-stage-")
        self.front = FRONT_ROOT / "releases" / f"passenger-{self.revision[:7]}-{tag}"
        self.assets = FRONT_ROOT / f"act-static-passenger-{self.revision[:7]}-{tag}"
        self.name = "act-passenger-" + self.revision[:7]

    def unused_port(self):
        require(not self.command("candidate-port", ["/usr/bin/ss", "-H", "-ltn", "sport = :3004"]).strip(),
                "Candidate port 3004 is occupied; no process touched.")

    def validate_routes(self):
        for name in ("candidate", "rollback"):
            path = self.record / (name + "-validation.conf")
            write_new(path, validation_master(regular(MASTER), sorted(SITE.parent.iterdir()), self.record / (name + ".conf")))
            self.command("nginx-validate-" + name, ["/usr/sbin/nginx", "-t", "-c", path, "-p", "/etc/nginx/"], log=True)

    def prepare(self):
        require(not self.retry_after_rollback, "A rollback retry may not rebuild the prepared frontend.")
        self.capture_baseline()
        self.unused_port()
        private(BACKUP)
        self.record = Path(tempfile.mkdtemp(prefix="passenger-stage-", dir=BACKUP))
        self.record.chmod(0o700)
        self.work = self.record
        self.paths()
        self.journal("PREPARATION_STARTED")
        print("PRIVATE_STAGING_RECORD=" + str(self.record), flush=True)
        self.phase = "export reviewed frontend"
        self.require_source(fetch=True)
        require(not self.front.exists() and not self.front.is_symlink(), "Candidate directory exists; preserved.")
        self.front.mkdir(mode=0o750)
        archive_data = self.git("archive", "--format=tar", self.revision, "act_website-main")
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:") as archive:
            for entry in archive.getmembers():
                parts = PurePosixPath(entry.name).parts
                require(parts and parts[0] == "act_website-main" and ".." not in parts and not entry.name.startswith("/")
                        and (entry.isdir() or entry.isfile()), "Unsafe source archive member.")
                target = self.front.joinpath(*parts[1:])
                if entry.isdir():
                    target.mkdir(mode=0o750, parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
                    with archive.extractfile(entry) as stream:
                        write_new(target, stream.read(), 0o750 if entry.mode & 0o111 else 0o640)
        source = tree(self.front)
        for name in ENV_FILES:
            require(not (self.front / name).exists(), "Committed source contains a runtime environment file.")
            if name in self.baseline["env_hashes"]:
                write_new(self.front / name, regular(OLD_FRONT / name))
        owner = pwd.getpwnam("act")
        for current, directories, files in os.walk(self.front):
            for path in [Path(current), *(Path(current) / name for name in files)]:
                os.chown(path, owner.pw_uid, owner.pw_gid)
        write_new(self.record / "public-environment.json", encoded(self.public))
        self.phase = "build inactive frontend"
        print("Building one inactive passenger-page frontend; current services remain untouched.", flush=True)
        environment = act_env() | self.public | {"npm_config_update_notifier": "false"}
        self.command("npm-ci", ["/usr/sbin/runuser", "-u", "act", "--", NPM, "ci", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund"],
                     env=environment, cwd=self.front, timeout=300, log=True)
        self.command("frontend-build", ["/usr/sbin/runuser", "-u", "act", "--", NODE, self.front / "node_modules/next/dist/bin/next", "build"],
                     env=environment, cwd=self.front, timeout=300, log=True)
        require(all(sha(regular(self.front / path)) == digest for path, digest in source.items()), "Build changed committed source.")
        build_id = regular(self.front / ".next/BUILD_ID").decode().strip()
        require(re.fullmatch(r"[A-Za-z0-9_-]{1,128}", build_id), "Candidate build identity is missing or invalid.")
        manifests = {"source": source, "build": tree(self.front / ".next", excluded=("cache",)),
                     "assets": copy_assets((OLD_ASSETS, self.front / ".next/static"), self.assets)}
        original = regular(self.site)
        candidate, rollback = route_pair(original, self.assets)
        for name, content in (("original", original), ("candidate", candidate), ("rollback", rollback)):
            write_new(self.record / (name + ".conf"), content)
        self.validate_routes()
        for name, manifest in manifests.items():
            write_new(self.record / (name + "-manifest.json"), encoded(manifest))
        self.invariants(self.baseline["old_site_hash"])
        self.retained(self.rows())
        self.environment_files_unchanged()
        require(sha(regular(DUMP)) == self.baseline["dump_hash"] and self.public_environment(self.rows()) == self.public,
                "Current startup or public configuration changed during preparation.")
        plan = {"schema": 1, "state": "PREPARED_NOT_ACTIVE", "frontend_sha": self.revision, "prior_frontend_sha": OLD_SHA,
                "backend_sha": BACK_SHA, "backend_changed": False, "front": str(self.front), "assets": str(self.assets),
                "name": self.name, "port": 3004, "site": str(self.site), "build_id": build_id, "baseline": self.baseline,
                "public_hash": sha(regular(self.record / "public-environment.json")),
                "manifests": {name: sha(regular(self.record / (name + "-manifest.json"))) for name in manifests},
                "configs": {name: sha(regular(self.record / (name + ".conf"))) for name in ("original", "candidate", "rollback")}}
        write_new(self.record / "plan.json", encoded(plan))
        self.journal("PREPARED_NOT_ACTIVE")
        print("PASSENGER FRONTEND BUILT AND ROUTING PREPARED - NOT ACTIVATED", flush=True)
        print("FRONTEND_SHA=" + self.revision, flush=True)
        print("BACKEND_UNCHANGED=" + BACK_SHA, flush=True)

    def retry_history(self, plan):
        require(self.record == BACKUP / "passenger-stage-eoszulb3" and self.revision == REVIEWED_SHA,
                "Retry is restricted to the approved eoszulb3 passenger frontend.")
        previous = self.record / "activation"
        private(previous)
        require(all(not (previous / (state + ".json")).exists()
                    and not (previous / (state + ".json")).is_symlink()
                    for state in ("ACTIVATED", "RECOVERY_INCOMPLETE")),
                "Previous activation is successful or recovery is incomplete; retry refused.")
        receipts = {}
        for state in ("NGINX_RELOAD_STARTED", "FRONTEND_ROLLED_BACK"):
            raw = regular(previous / (state + ".json"))
            receipt = json.loads(raw)
            require(receipt.get("state") == state and receipt.get("frontend_sha") == REVIEWED_SHA
                    and receipt.get("backend_sha") == BACK_SHA and receipt.get("backend_changed") is False
                    and receipt.get("journey_accepted") is False,
                    "The previous frontend rollback receipt differs; retry refused.")
            receipts[state] = sha(raw)
        dump = regular(previous / "dump.pm2.before")
        require(sha(dump) == plan["baseline"]["dump_hash"] and regular(DUMP) == dump,
                "Original PM2 startup preimage was not restored; retry refused.")
        return {"original_activation": str(previous), "original_plan_sha256": sha(regular(self.record / "plan.json")),
                "receipts": receipts, "dump_sha256": sha(dump), "original_configs": plan["configs"]}

    def preflight(self):
        self.paths()
        private(self.record)
        work = self.record / ("activation-retry" if self.retry_after_rollback else "activation")
        require(not work.exists() and not work.is_symlink(),
                "Activation was already attempted; review its record before retrying.")
        plan = json.loads(regular(self.record / "plan.json"))
        require(plan.get("schema") == 1 and plan.get("state") == "PREPARED_NOT_ACTIVE"
                and plan.get("frontend_sha") == self.revision and plan.get("prior_frontend_sha") == OLD_SHA
                and plan.get("backend_sha") == BACK_SHA and plan.get("backend_changed") is False
                and plan.get("front") == str(self.front) and plan.get("assets") == str(self.assets)
                and plan.get("name") == self.name and plan.get("port") == 3004, "Prepared plan does not match this exact release.")
        require(set(plan.get("manifests", {})) == {"source", "build", "assets"}
                and set(plan.get("configs", {})) == {"original", "candidate", "rollback"}, "Prepared evidence is incomplete.")
        self.original, self.candidate, self.rollback = [regular(self.record / (name + ".conf")) for name in ("original", "candidate", "rollback")]
        require({name: sha(data) for name, data in zip(("original", "candidate", "rollback"), (self.original, self.candidate, self.rollback))} == plan["configs"]
                and route_pair(self.original, self.assets) == (self.candidate, self.rollback), "Prepared routing exceeds the reviewed change.")
        expected_baseline = copy.deepcopy(plan["baseline"])
        if self.retry_after_rollback:
            self.retry_provenance = self.retry_history(plan)
            require(expected_baseline["old_site_hash"] == sha(self.original), "Original routing baseline differs.")
            expected_baseline["old_site_hash"] = sha(self.rollback)
        self.capture_baseline()
        require(self.baseline == expected_baseline and str(self.site) == plan["site"], "Activation baseline drifted since preparation.")
        self.require_source()
        self.unused_port()
        self.environment_files_unchanged()
        require(sha(regular(self.record / "public-environment.json")) == plan["public_hash"]
                and json.loads(regular(self.record / "public-environment.json")) == self.public, "Prepared public configuration changed.")
        for name, digest in plan["manifests"].items():
            require(name in ("source", "build", "assets"), "Unexpected manifest type.")
            raw = regular(self.record / (name + "-manifest.json"))
            require(sha(raw) == digest, "Prepared manifest changed.")
            manifest = json.loads(raw)
            if name == "source":
                require(all(not PurePosixPath(path).is_absolute() and ".." not in PurePosixPath(path).parts
                            and sha(regular(self.front / path)) == value for path, value in manifest.items()), "Candidate source changed.")
            else:
                require(tree(self.front / ".next", excluded=("cache",)) == manifest if name == "build" else tree(self.assets) == manifest,
                        "Prepared build or assets changed.")
            if name == "assets":
                self.asset_map = manifest
        self.build_id = plan["build_id"].encode()
        require(regular(self.front / ".next/BUILD_ID").strip() == self.build_id, "Prepared build ID changed.")
        self.dump_before = regular(DUMP)
        self.saved_before = json.loads(self.dump_before)
        # Claim only a newly created journal. A refused duplicate never writes
        # STOPPED_BEFORE_ACTIVATION into somebody else's previous attempt.
        work.mkdir(mode=0o700)
        self.work = work
        if self.retry_after_rollback:
            self.original = self.rollback
            write_new(self.work / "retry-provenance.json", encoded(self.retry_provenance))
        write_new(self.work / "dump.pm2.before", self.dump_before)
        self.journal("PREFLIGHT_COMPLETE")
        print("PRIVATE_ACTIVATION_RECORD=" + str(self.work), flush=True)

    def pm2_payload(self):
        return {"socket": str(PM2_HOME / "rpc.sock"), "pid_file": str(PM2_HOME / "pm2.pid"), "daemon_pid": self.daemon,
                "retained": self.baseline["retained"], "identity_fields": list(IDENTITY)}

    def candidate_row(self, rows):
        self.retained(rows, True)
        row = one(rows, self.name)
        value = row["pm2_env"]
        require(row["pid"] > 1 and value.get("status") == "online" and value.get("pm_cwd") == str(self.front)
                and value.get("pm_exec_path") == str(self.front / "node_modules/next/dist/bin/next")
                and value.get("exec_interpreter") == str(NODE) and value.get("args") == ARGS
                and value.get("exec_mode") == "fork_mode" and all(value.get(key) == expected for key, expected in POLICY.items())
                and Path(f'/proc/{row["pid"]}/cwd').resolve(strict=True) == self.front
                and value.get("env", {}).get("ACT_TRACKING_ACTIVATION") == str(self.work)
                and all(value.get("env", {}).get(key) == expected for key, expected in self.public.items()), "Candidate launch identity differs.")
        return row

    def http(self, target, path="/en"):
        require(path.startswith("/") and not any(char in path for char in ("\r", "\n")), "Invalid release-readiness path.")
        args = ["/usr/bin/curl", "--silent", "--show-error", "--noproxy", "*", "--connect-timeout", "3", "--max-time", "8",
                "--max-filesize", "16777216", "-H", "Accept-Encoding: identity", "-H", "Cache-Control: no-cache", "-w", "\n%{http_code}"]
        page_metadata = target in ("origin", "public") and path == "/en"
        header_file = None
        if page_metadata:
            self.response_metadata = {}
            descriptor, filename = tempfile.mkstemp(prefix=".readiness-headers-", dir=self.work)
            os.close(descriptor)
            header_file = Path(filename)
            args += ["--dump-header", header_file]
        if target in ("3003", "3004"):
            args += ["-H", "Host: " + DOMAIN, "-H", "X-Forwarded-Proto: https", "http://127.0.0.1:" + target + path]
        else:
            require(target in ("origin", "public"), "Unexpected readiness target.")
            if target == "origin":
                # Preserve the reviewed origin-certificate exception on loopback only.
                args += ["--insecure", "--resolve", DOMAIN + ":443:127.0.0.1"]
            nonce = getattr(self, "probe_nonce", None) or secrets.token_hex(12)
            args += [ORIGIN + path + ("&" if "?" in path else "?") + "act_release_check=" + self.record.name + "-" + nonce]
        try:
            body, code = self.command("frontend-integrity", args, timeout=12).rsplit(b"\n", 1)
            if page_metadata and re.fullmatch(rb"[0-9]{3}", code):
                self.response_metadata["http_status"] = int(code)
        finally:
            if header_file is not None:
                try:
                    with header_file.open("rb") as stream:
                        self.response_metadata.update(cache_metadata(stream.read(32768)))
                finally:
                    header_file.unlink(missing_ok=True)
        require(code == b"200", "Frontend release-readiness request failed.")
        return body

    def build_classification(self, body):
        current = self.build_id in body
        previous = self.baseline["old_build_id"].encode() in body
        return "mixed" if current and previous else "expected" if current else "old" if previous else "missing"

    def verify_public(self, new):
        expected = self.new_paths if new else self.old_paths
        for attempt in range(1, 4):
            self.probe_nonce = secrets.token_hex(12)
            try:
                for target in ("origin", "public"):
                    report = {"direction": "activation" if new else "rollback", "attempt": attempt, "target": target,
                              "required_build": "expected" if new else "old", "build_id": "missing", "check": "page_request", "result": "failed"}
                    self.response_metadata = {}
                    try:
                        body = self.http(target)
                        report["build_id"] = self.build_classification(body)
                        report["check"] = "asset_paths"
                        require(html_assets(body) == expected, "Public routing serves unexpected build assets.")
                        if self.new_paths == self.old_paths:
                            report["check"] = "build_id"
                            require(self.build_id != self.baseline["old_build_id"].encode()
                                    and report["build_id"] == report["required_build"],
                                    "Public routing serves the wrong frontend build ID.")
                        report["check"] = "asset_hashes"
                        for asset in self.check_assets:
                            require(sha(self.http(target, quote(asset, safe="/._-"))) == self.asset_map[asset.removeprefix("/_next/static/")],
                                    "Public old/new build asset differs from the prepared bytes.")
                        report["result"] = "passed"
                    finally:
                        print("FRONTEND_READINESS " + json.dumps(report | self.response_metadata, sort_keys=True), flush=True)
                return
            except (Stop, OSError, ValueError):
                if attempt == 3:
                    raise
                time.sleep(2)

    def activate(self):
        self.invariants(sha(self.original))
        self.retained(self.rows())
        require(regular(DUMP) == self.dump_before, "Saved startup state changed before activation.")
        old_body = self.http("3003")
        self.old_paths = html_assets(old_body)
        self.phase = "start candidate frontend"
        config = {"name": self.name, "cwd": str(self.front), "script": str(self.front / "node_modules/next/dist/bin/next"),
                  "interpreter": str(NODE), "args": ARGS, "exec_mode": "fork", "instances": 1, "watch": False,
                  "env": {"NODE_ENV": "production", "NEXT_TELEMETRY_DISABLED": "1", "ACT_TRACKING_ACTIVATION": str(self.work), **self.public}, **POLICY}
        self.journal("CANDIDATE_START_STARTED")
        self.start_attempted = True
        self.command("pm2-start-candidate", ["/usr/sbin/runuser", "-u", "act", "--", NODE, "-e", PM2_START, PM2_ROOT],
                     env=act_env(), data=encoded(self.pm2_payload() | {"config": config, "policy": POLICY}), timeout=30, log=True)
        self.start_acknowledged = True
        for attempt in range(5):
            try:
                row = self.candidate_row(self.rows())
                body = self.http("3004")
                self.new_paths = html_assets(body)
                require(self.new_paths and (self.new_paths != self.old_paths or
                        (self.build_id != self.baseline["old_build_id"].encode() and self.build_id in body
                         and self.build_id not in old_body and self.baseline["old_build_id"].encode() in old_body
                         and self.baseline["old_build_id"].encode() not in body)), "Candidate build identity is not distinguishable.")
                break
            except (Stop, OSError, ValueError):
                if attempt == 4:
                    raise Stop("Bounded candidate readiness failed.") from None
                time.sleep(1)
        self.check_assets = sorted({next((path for path in sorted(paths) if path.endswith(extension)), "")
                                  for paths in (self.old_paths, self.new_paths) for extension in (".js", ".css")})
        require("" not in self.check_assets and all(path.removeprefix("/_next/static/") in self.asset_map for path in self.check_assets), "Old/new build assets are absent from the union.")
        self.candidate_identity = identity(row)
        self.phase = "persist candidate startup"
        self.invariants(sha(self.original))
        require(regular(DUMP) == self.dump_before and identity(self.candidate_row(self.rows())) == self.candidate_identity, "Startup or candidate drift before persistence.")
        saved = copy.deepcopy(row["pm2_env"])
        for key in ("instances", "pm_id", "prev_restart_delay", "_tree_pids"):
            saved.pop(key, None)
        self.dump_new = encoded([*self.saved_before, saved])
        self.journal("PERSISTENCE_STARTED")
        self.dump_attempted = True
        atomic_file(DUMP, self.dump_new, sha(self.dump_before))
        require(json.loads(regular(DUMP)) == [*self.saved_before, saved], "Candidate startup persistence differs.")
        self.phase = "switch frontend routing"
        self.invariants(sha(self.original))
        require(regular(DUMP) == self.dump_new and identity(self.candidate_row(self.rows())) == self.candidate_identity, "Candidate drift before routing.")
        self.journal("ROUTING_STARTED")
        self.route_attempted = True
        atomic_file(self.site, self.candidate, sha(self.original))
        self.command("nginx-installed-validation", ["/usr/sbin/nginx", "-t"], log=True)
        self.journal("NGINX_RELOAD_STARTED")
        self.reload_attempted = True
        self.command("nginx-reload", ["/usr/bin/systemctl", "reload", "nginx.service"], log=True)
        self.verify_public(True)
        self.invariants(sha(self.candidate))
        require(regular(DUMP) == self.dump_new and identity(self.candidate_row(self.rows())) == self.candidate_identity, "Final startup identity differs.")
        self.journal("ACTIVATED")
        self.complete = True
        print("PASSENGER FRONTEND ACTIVATED - BACKEND UNCHANGED - JOURNEY NOT YET ACCEPTED", flush=True)

    def recover(self):
        if self.complete or not self.start_attempted:
            return
        self.phase = "recover only this frontend attempt"
        observed = sha(regular(self.site))
        allowed = (sha(self.candidate), sha(self.rollback)) if self.reload_attempted else (sha(self.original), sha(self.candidate))
        require(observed in allowed, "Concurrent routing edit; automatic recovery withheld.")
        self.invariants(observed)
        if self.route_attempted:
            target = self.rollback if self.reload_attempted else self.original
            if observed != sha(target):
                atomic_file(self.site, target, observed)
            self.command("nginx-rollback-validation", ["/usr/sbin/nginx", "-t"], log=True)
            if self.reload_attempted:
                self.command("nginx-rollback-reload", ["/usr/bin/systemctl", "reload", "nginx.service"], log=True)
                self.verify_public(False)
        current = sha(regular(DUMP))
        permitted = (sha(self.dump_before), sha(self.dump_new)) if self.dump_attempted else (sha(self.dump_before),)
        require(current in permitted, "Concurrent startup edit; automatic recovery withheld.")
        if current != sha(self.dump_before):
            atomic_file(DUMP, self.dump_before, current)
        payload = self.pm2_payload() | {"name": self.name, "cwd": str(self.front), "script": str(self.front / "node_modules/next/dist/bin/next"),
                   "interpreter": str(NODE), "args": ARGS, "activation_nonce": str(self.work), "allow_absent": self.start_acknowledged}
        self.command("remove-only-candidate", ["/usr/sbin/runuser", "-u", "act", "--", NODE, "-e", PM2_REMOVE, PM2_ROOT],
                     env=act_env(), data=encoded(payload), timeout=30, log=True)
        self.retained(self.rows())
        require(self.backend() == self.baseline["backend"], "Backend changed during recovery; no backend action taken.")
        self.journal("FRONTEND_ROLLED_BACK")
        print("FRONTEND RETURNED TO 3a82c16 ON 3003 - BACKEND UNCHANGED", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--activate", action="store_true", help="Only after approval of the exact built frontend SHA.")
    parser.add_argument("--frontend-sha", required=True)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--retry-after-rollback", action="store_true",
                        help="One reviewed retry of eoszulb3 after its completed frontend rollback; no rebuild.")
    args = parser.parse_args(argv)
    require(args.frontend_sha == REVIEWED_SHA, "Supply the exact reviewed passenger-page frontend SHA.")
    require((args.prepare and args.record is None) or (args.activate and args.record is not None), "Only activation accepts a prepared record.")
    require(not args.retry_after_rollback or (args.activate and args.record == BACKUP / "passenger-stage-eoszulb3"),
            "Rollback retry requires --activate and the exact eoszulb3 record.")
    require(os.geteuid() == 0, "Use the existing authorised root Hostinger terminal.")
    os.umask(0o077)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    def interrupt(_signal, _frame):
        raise Stop("Operator interrupted the release.")
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    operation = Release(args.frontend_sha, args.record, args.retry_after_rollback)
    with Path("/run/lock/act-backend-deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args.prepare:
                operation.prepare()
            else:
                operation.preflight()
                operation.activate()
            return 0
        except (Exception, KeyboardInterrupt) as error:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            print("STOP [" + operation.phase + "]: " + (str(error) if isinstance(error, Stop) else "Local release operation failed; details are private."), flush=True)
            try:
                if operation.work and not operation.start_attempted:
                    operation.journal("PREPARATION_FAILED" if args.prepare else "STOPPED_BEFORE_ACTIVATION")
                operation.recover()
            except (Exception, KeyboardInterrupt):
                if operation.work:
                    operation.journal("RECOVERY_INCOMPLETE")
                print("Recovery incomplete. Preserve this record; do not rerun or restart other services.", flush=True)
            return 1
        finally:
            if operation.record:
                print("PRIVATE_RELEASE_RECORD=" + str(operation.record), flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Stop, OSError, ValueError):
        print("STOP: Required input, record or release lock is unavailable; no raw exception output.")
        raise SystemExit(1) from None
