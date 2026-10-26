"""Prepare policy-review artifacts; never publish, configure Django or call APIs.

Invoked by the existing build-customer-documents.py --review-bundle entry point.
The source Markdown is pinned by SHA-256. Only the specified sections are rendered;
wording is not rewritten, translated or completed by this generator.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
FORMAT = "act-policy-review-bundle-v1"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HASH = re.compile(r"[0-9a-f]{64}")
WARNING = "REVIEW ONLY - NOT PUBLISHED OR EFFECTIVE"
CSS = '''@page {size:A4;margin:19mm 19mm 21mm;
 @bottom-left{content:"ACT | REVIEW ONLY - NOT EFFECTIVE";font:8pt sans-serif;color:#666;}
 @bottom-right{content:counter(page) " / " counter(pages);font:8pt sans-serif;color:#666;}}
body{font-family:"DejaVu Sans",sans-serif;font-size:9.6pt;line-height:1.42;color:#202020;}
header{border-bottom:3px solid #dfb900;padding-bottom:9px;margin-bottom:12px;font-size:10pt;}
h1{font-size:21pt;line-height:1.25;color:#142039;margin:10px 0 14px;}
h2{font-size:11pt;line-height:1.35;color:#142039;margin:14px 0 5px;break-after:avoid;}
p{margin:6px 0;orphans:3;widows:3;overflow-wrap:anywhere;}
.flag{background:#f3f0e5;border-left:4px solid #b08b00;padding:10px;font-weight:bold;font-size:9pt;}
.note{font-size:8pt;color:#555;border-top:1px solid #bbb;margin-top:16px;padding-top:10px;}
.version{font-size:8.5pt;color:#555;}a{color:#142039;}
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def relative_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Invalid relative file")
    p = Path(name)
    if p.is_absolute() or any(part in ("..", ".") for part in p.parts):
        raise ValueError("Unsafe relative file")
    root = root.resolve()
    target = root / p
    cursor = root
    for part in p.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink paths are not accepted")
    if not target.resolve().is_relative_to(root):
        raise ValueError("Path escapes bundle root")
    return target


def load_spec(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema") != 1 or spec.get("state") != "review_only":
        raise ValueError("Only review-only preparation is supported")
    if spec.get("published") is not False or spec.get("effective_at") is not None:
        raise ValueError("Preparation cannot publish or set an effective date")
    if not SLUG.fullmatch(spec.get("bundle_id", "")) or not spec.get("publication_holds"):
        raise ValueError("Review identity and unresolved holds are required")
    if spec.get("policy_version") != "act-cancellation-24h12h-v1":
        raise ValueError("Unreviewed calculation policy")
    if spec.get("required_checkout_locales") != ["en", "ar"]:
        raise ValueError("Preserve the current English/Arabic release requirement")
    docs = spec.get("documents")
    if not isinstance(docs, list) or not docs:
        raise ValueError("Document list required")
    seen = set()
    for doc in docs:
        if not SLUG.fullmatch(doc.get("id", "")) or doc["id"] in seen:
            raise ValueError("Invalid or duplicate document ID")
        seen.add(doc["id"])
        if doc.get("locale") != "en":
            raise ValueError("Only the actually reviewed English sources are supplied; do not invent translations")
        if not HASH.fullmatch(doc.get("source_sha256", "")):
            raise ValueError("Pinned source hash required")
        if not all(isinstance(doc.get(k), str) and doc[k].strip()
                   for k in ("title", "version", "source", "start", "end")):
            raise ValueError("Incomplete document source specification")
    if seen != {"customer-booking-terms", "driver-application-terms", "driver-privacy-notice"}:
        raise ValueError("Keep customer terms, driver terms and driver privacy distinct")
    return spec


def selected_source(doc: dict, root: Path) -> tuple[bytes, str]:
    raw = relative_file(root, doc["source"]).read_bytes()
    if sha(raw) != doc["source_sha256"]:
        raise ValueError("Source changed since review: " + doc["source"])
    text = raw.decode("utf-8")
    start, end = doc["start"], doc["end"]
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError("Section boundaries missing or duplicated")
    a, b = text.index(start) + len(start), text.index(end)
    if b <= a:
        raise ValueError("Section order invalid")
    body = text[a:b].strip() + "\n"
    for marker in doc.get("required_phrases", []):
        if marker not in body:
            raise ValueError("Required approved wording missing")
    return raw, body


def plain_inline(text: str) -> str:
    # Formatting only. Preserve legal/reference words, punctuation and order.
    # Any actual HTML is escaped later, never interpreted or fetched.
    return text.replace("**", "")


def blocks(markdown: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for chunk in re.split(r"\n\s*\n", markdown.strip()):
        lines = chunk.splitlines()
        paragraph: list[str] = []
        def flush() -> None:
            if paragraph:
                result.append(("p", plain_inline(" ".join(paragraph))))
                paragraph.clear()
        for line in lines:
            if line.startswith("### "):
                flush(); result.append(("h2", plain_inline(line[4:])))
            elif line.startswith("- "):
                flush(); result.append(("p", plain_inline(line)))
            else:
                paragraph.append(line)
        flush()
    return result


def canonical(doc: dict, markdown: str) -> str:
    return doc["title"] + "\n\n" + "\n\n".join(value for _, value in blocks(markdown)) + "\n"


def markup(doc: dict, markdown: str) -> str:
    e = html.escape
    content = "".join(f"<{tag}>{e(value)}</{tag}>" for tag, value in blocks(markdown))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{e(doc['title'])} - review</title><style>{CSS}</style></head><body>
<header>Airport &amp; City Transfer | English</header>
<p class="flag">{WARNING}</p><p class="version">{e(doc['version'])}</p>
<h1>{e(doc['title'])}</h1>{content}
<p class="note">Review copy extracted without substantive changes from the pinned source.
Reference markers refer to the complete review source included in this bundle.
Unresolved publication notes remain visible; this is not a live customer contract.</p>
</body></html>'''


def render_pdf(source: str) -> bytes:
    from weasyprint import HTML
    def reject_resource(url: str, *args: Any, **kwargs: Any) -> None:
        raise ValueError("External and local URL resources are disabled")
    return HTML(string=source, url_fetcher=reject_resource).write_pdf()


def assert_output_safe(output: Path, root: Path) -> None:
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; existing bundle preserved")
    for parent in output.parents:
        if parent.is_symlink():
            raise ValueError("Output cannot traverse a symlink")
    root = root.resolve()
    # A review artifact must not accidentally become a deployed public download.
    if output.resolve().is_relative_to(root / "act_website-main" / "public"):
        raise ValueError("Review output cannot be written under website public paths")
    if not output.parent.is_dir():
        raise ValueError("Create the intended review-output parent first")


def build_bundle(spec_path: Path, output: Path, root: Path = REPO) -> dict:
    spec = load_spec(spec_path)
    assert_output_safe(output, root)
    # Validate every source before generating or writing any result.
    inputs = [(doc, *selected_source(doc, root)) for doc in spec["documents"]]
    with tempfile.TemporaryDirectory(prefix="act-policy-review-", dir=output.parent) as temp:
        stage = Path(temp) / "bundle"
        stage.mkdir()
        def write(name: str, data: str | bytes) -> None:
            p = relative_file(stage, name); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        documents = {}
        for doc, raw, body in inputs:
            text = canonical(doc, body)
            rendered = markup(doc, body)
            pdf = render_pdf(rendered)
            if not pdf.startswith(b"%PDF-"):
                raise ValueError("Renderer did not return a PDF")
            text_hash, pdf_hash = sha(text.encode()), sha(pdf)
            filename = f"{text_hash[:16]}-{pdf_hash[:16]}.pdf"
            target = f"documents/en/{doc['id']}/{filename}"
            text_path = f"texts/en/{doc['id']}.txt"
            html_path = f"previews/en/{doc['id']}.html"
            write(target, pdf); write(text_path, text); write(html_path, rendered)
            write(f"sources/{Path(doc['source']).name}", raw)
            write(f"sections/en/{doc['id']}.md", body)
            documents[doc["id"]] = {
                "title": doc["title"], "version": doc["version"], "locale": "en",
                "source": doc["source"], "source_sha256": doc["source_sha256"],
                "section_sha256": sha(body.encode()), "text_path": text_path,
                "text_sha256": text_hash, "pdf_path": target, "pdf_sha256": pdf_hash,
                "preview_path": html_path, "proposed_document_url": "/" + target,
                "published": False,
            }
        customer = documents["customer-booking-terms"]
        text = relative_file(stage, customer["text_path"]).read_text(encoding="utf-8")
        release = {"published": False, "effective_at": None,
                   "terms_version": customer["version"], "policy_version": spec["policy_version"],
                   "locales": {"en": {"text": text, "sha256": customer["text_sha256"],
                       "url": customer["proposed_document_url"], "pdf_sha256": customer["pdf_sha256"]}}}
        write("checkout-release.candidate.json", dump(release))
        links = {"state": "review_only", "runtime_wired": False,
                 "checkout_customer_terms": customer["proposed_document_url"],
                 "driver_application_terms": documents["driver-application-terms"]["proposed_document_url"],
                 "driver_application_privacy": documents["driver-privacy-notice"]["proposed_document_url"],
                 "customer_privacy": None, "missing_checkout_locales": ["ar"]}
        write("document-links.candidate.json", dump(links))
        write("review-input.json", dump(spec))
        items = "".join(f'<li><b>{html.escape(d["title"])}</b>: '
                       f'<a href="{d["preview_path"]}">HTML review</a> | '
                       f'<a href="{d["pdf_path"]}">PDF review</a></li>' for d in documents.values())
        holds = "".join(f'<li>{html.escape(h)}</li>' for h in spec["publication_holds"])
        write("index.html", f'<!doctype html><html lang="en"><meta charset="utf-8"><title>ACT policy review</title>'
              f'<style>{CSS}</style><body><h1>ACT policy review bundle</h1><p class="flag">{WARNING}</p>'
              f'<ul>{items}</ul><h2>Publication holds</h2><ul>{holds}</ul>'
              '<p>Arabic is not supplied; no silent English fallback. Customer privacy is separate and not replaced by driver privacy.</p></body></html>')
        write("README.txt", "ACT POLICY REVIEW BUNDLE - NOT A DEPLOYMENT PACKAGE\n\n"
              "All PDF, HTML and checkout-text outputs share pinned source sections.\n"
              "Only Markdown heading/bold presentation and paragraph whitespace are normalised.\n"
              "No substantive policy changes; original full sources and references are included.\n"
              "The checkout candidate is published=false with no effective date; do not load it as production settings.\n"
              "Proposed public URLs are mappings, not verified live links. HTML/PDF review links in index.html are local.\n"
              "No Arabic translation or customer privacy finalisation is claimed.\n"
              "Hashes prove local artifact consistency, not legal approval, finality or live PDF hosting.\n"
              "No existing website dictionary, public PDF, confirmation/cancellation receipt or database is changed.\n")
        files = {str(p.relative_to(stage)): sha(p.read_bytes()) for p in sorted(stage.rglob("*")) if p.is_file()}
        receipt = {"format": FORMAT, "state": "review_only", "bundle_id": spec["bundle_id"],
                   "published": False, "effective_at": None, "runtime_wired": False,
                   "source_revision": spec["source_revision"], "documents": documents,
                   "publication_holds": spec["publication_holds"], "files": files}
        write("bundle-manifest.json", dump(receipt))
        verify_bundle(stage)
        # Destination was required absent. Never merge with or overwrite another bundle.
        if output.exists():
            raise ValueError("Output appeared during preparation; existing files preserved")
        stage.rename(output)
    return receipt


def verify_bundle(root: Path) -> dict:
    receipt = json.loads(relative_file(root, "bundle-manifest.json").read_text(encoding="utf-8"))
    if (receipt.get("format") != FORMAT or receipt.get("published") is not False
            or receipt.get("state") != "review_only" or receipt.get("effective_at") is not None
            or receipt.get("runtime_wired") is not False):
        raise ValueError("Review bundle cannot represent a published release")
    expected_files = set(receipt["files"]) | {"bundle-manifest.json"}
    actual_files = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink()}
    if expected_files != actual_files:
        raise ValueError("Bundle file inventory changed")
    for name, checksum in receipt["files"].items():
        if sha(relative_file(root, name).read_bytes()) != checksum:
            raise ValueError("Bundle content mismatch: " + name)
    release = json.loads(relative_file(root, "checkout-release.candidate.json").read_text(encoding="utf-8"))
    if release["published"] is not False or release["effective_at"] is not None:
        raise ValueError("Candidate checkout activation is forbidden")
    for ident, doc in receipt["documents"].items():
        txt = relative_file(root, doc["text_path"]).read_bytes()
        pdf = relative_file(root, doc["pdf_path"]).read_bytes()
        if sha(txt) != doc["text_sha256"] or sha(pdf) != doc["pdf_sha256"] or not pdf.startswith(b"%PDF-"):
            raise ValueError("Document content/hash mismatch")
        if doc["proposed_document_url"] != "/" + doc["pdf_path"] or doc["published"] is not False:
            raise ValueError("Incorrect proposed document mapping")
        if ident == "customer-booking-terms":
            descriptor = release["locales"]["en"]
            if descriptor != {"text": txt.decode(), "sha256": doc["text_sha256"],
                              "url": doc["proposed_document_url"], "pdf_sha256": doc["pdf_sha256"]}:
                raise ValueError("Checkout and downloadable terms differ")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-bundle", type=Path, help="Pinned review input JSON; prepare only")
    parser.add_argument("--output", type=Path, help="New non-public review artifact directory")
    parser.add_argument("--verify-review-bundle", type=Path)
    args = parser.parse_args()
    try:
        if args.verify_review_bundle:
            if args.review_bundle or args.output:
                parser.error("Verify and build are separate operations")
            verify_bundle(args.verify_review_bundle)
            print("POLICY REVIEW BUNDLE HASHES VERIFIED - NO PUBLICATION")
        else:
            if not args.review_bundle or not args.output:
                parser.error("--review-bundle and --output are both required")
            build_bundle(args.review_bundle, args.output)
            print("THREE MATCHED POLICY REVIEW DOCUMENTS PREPARED - NOT PUBLISHED")
        return 0
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        parser.exit(1, "STOP: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
