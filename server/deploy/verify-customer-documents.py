"""Offline acceptance check for the approved ACT English/Arabic release."""
import ast
import hashlib
import json
import logging
import os
from pathlib import Path
from io import BytesIO
import sys
import tempfile
import unittest

EXPECTED_SHA = "a111eb4767951a6c5b76a87cc9ce3e5ec1525337"
root = Path("/var/www/atg/atg-backend/current").resolve(strict=True)
assert json.loads((root / "release.json").read_text())["git_sha"] == EXPECTED_SHA
os.environ.pop("DJANGO_SETTINGS_MODULE", None)
sys.dont_write_bytecode = True
sys.path.insert(0, str(root))
from apps.trips.tests import test_customer_language as checks
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(checks))
assert result.wasSuccessful(), "Offline language tests failed"
from django.conf import settings
from weasyprint import HTML
from apps.trips.services.customer_language import booking_language
from apps.trips.services.customer_documents import render_arabic_document
logo = root / "static/assets/act_logo.png"
assert logo.is_file(), "Production logo missing"
assert logo.read_bytes().startswith(bytes([137, 80, 78, 71])), "Logo is not a readable PNG"

# Use the deployed PDF functions with isolated template settings. Their Arabic
# branches access no database, maps service, payments or outgoing messages.
source = ast.parse((root / "apps/trips/services/pdf_generator.py").read_text())
names = {"generate_booking_confirmation_pdf", "generate_cancellation_confirmation_pdf"}
module = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
assert len(module.body) == 2
env = dict(Path=Path, BytesIO=BytesIO, settings=settings, HTML=HTML,
           booking_language=booking_language, render_arabic_document=render_arabic_document)
exec(compile(module, "deployed_pdf_functions", "exec"), env)

class FailOnRenderError(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            raise RuntimeError(record.getMessage())

logging.getLogger("weasyprint").addHandler(FailOnRenderError())
trip = checks.sample("ar")
trip.booking_details["additional_requirements"]["notes_to_driver"] = "Synthetic preview"
pdfs = {}
for kind in ("booking", "cancellation"):
    data = env["generate_" + kind + "_confirmation_pdf"](trip).getvalue()
    assert data.startswith(b"%PDF-") and len(data) > 5000
    pdfs[kind] = data

# Only these synthetic outputs are readable by the existing automation account.
# Production files, ownership and permissions are untouched.
out = Path(tempfile.mkdtemp(prefix="act-language-check-a111eb476795-", dir="/tmp"))
report = {"git_sha": EXPECTED_SHA, "tests_passed": result.testsRun, "pdfs": {}}
for kind, data in pdfs.items():
    p = out / (kind + "-ar.pdf")
    p.write_bytes(data)
    p.chmod(0o644)
    report["pdfs"][kind] = {"file": p.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
manifest = out / "verification.json"
manifest.write_text(json.dumps(report, indent=2))
manifest.chmod(0o644)
out.chmod(0o755)
print("LANGUAGE TESTS AND BOTH ARABIC PDF RENDERS PASSED")
print("OUTPUT:", out)
