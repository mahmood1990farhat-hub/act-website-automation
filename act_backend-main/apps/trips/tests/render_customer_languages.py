"""Render real production PDF function bodies with synthetic booking data only.

Run from the backend directory with Django, WeasyPrint and pypdf installed.
Chinese acceptance requires an installed Noto Sans CJK SC font. This does not
contact Maps, Stripe, a database, an email server or production storage.
"""
import argparse
import ast
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess

from pypdf import PdfReader
from weasyprint import HTML

from apps.trips.tests.test_customer_language import (
    BASE, sample, settings, booking_language, render_customer_document,
    format_booking_details_for_email, render_to_string,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    fonts = subprocess.run(["fc-list", ":lang=zh", "family"], capture_output=True, text=True, check=True).stdout
    if "Noto Sans CJK SC" not in fonts:
        raise RuntimeError("Install Noto Sans CJK SC before accepting Chinese PDF rendering")
    source_path = BASE / "apps/trips/services/pdf_generator.py"
    source = ast.parse(source_path.read_text())
    names = {"_money", "_booking_reference", "_payment_method_label", "_readable_location", "_passenger_name",
             "generate_booking_confirmation_pdf", "generate_cancellation_confirmation_pdf"}
    module = ast.Module(body=[node for node in source.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
    env = dict(globals(), place_to_string=lambda _: None)
    exec(compile(module, str(source_path), "exec"), env)
    manifest = []
    for locale in ("en", "ar", "fr", "de", "es", "tr", "zh-CN"):
        for kind in ("booking", "cancellation"):
            trip = sample(locale)
            # Include Chinese, Arabic and accented names in every language.
            trip.passenger_name = "张伟 / ليلى / Élodie Özdemir"
            trip.booking_details["additional_requirements"]["notes_to_driver"] = "Terminal 5 – 张伟 – ليلى"
            result = env["generate_" + kind + "_confirmation_pdf"](trip)
            path = output / (kind + "-" + locale + ".pdf")
            path.write_bytes(result.getvalue())
            reader = PdfReader(path)
            content = "\n".join(page.extract_text() for page in reader.pages)
            if not reader.pages or "ACT-000042" not in content:
                raise AssertionError(f"Missing booking reference: {path.name}")
            if locale in ("fr", "de", "es", "tr", "zh-CN"):
                from apps.trips.services.localized_documents import document_catalog
                if document_catalog(locale)[kind + "_title"] not in content:
                    raise AssertionError(f"Missing localized PDF title: {path.name}")
            manifest.append({"file": path.name, "locale": locale, "kind": kind, "pages": len(reader.pages), "bytes": path.stat().st_size})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
