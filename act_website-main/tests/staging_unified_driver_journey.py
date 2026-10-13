"""Ephemeral full-browser acceptance of ACT's unified driver journey.

Uses only GitHub runner localhost, a fresh PostGIS database, synthetic documents,
MailHog email and a disposable Chromium browser. NEVER targets production.
"""
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

from PIL import Image
from playwright.sync_api import sync_playwright, expect

WEB = "http://127.0.0.1:3001"
API = "http://127.0.0.1:8000"
MAIL = "http://127.0.0.1:8025"
EMAIL = "staging-applicant@example.invalid"
PASSWORD = "SyntheticJourneyPassword+2026"
ADMIN_EMAIL = "staging-admin@example.invalid"
ADMIN_PASSWORD = "StagingAdminPassword+2026"


def request_json(method, endpoint, payload=None, bearer=None):
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(
        API + endpoint,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def synthetic_pdf():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def synthetic_photo():
    buf = io.BytesIO()
    Image.new("RGB", (48, 48), color=(65, 85, 125)).save(buf, format="PNG")
    return buf.getvalue()


def future_date(days):
    return (date.today() + timedelta(days=days)).isoformat()


def find_welcome_link():
    for _ in range(35):
        with urllib.request.urlopen(MAIL + "/api/v2/messages", timeout=10) as result:
            messages = json.load(result).get("items", [])
        for item in messages:
            recipients = item.get("To", [])
            if not any(EMAIL in str(r.get("Mailbox", "")) + "@" + str(r.get("Domain", "")) for r in recipients):
                continue
            body = item.get("Content", {}).get("Body", "")
            match = re.search(r"http://127\.0\.0\.1:3001/en/driver-password-setup/#([A-Za-z0-9_-]+)", body)
            if match:
                return match.group(0)
        time.sleep(1)
    raise AssertionError("ACT's one-time password setup email was not delivered to isolated MailHog")


def fill(page, title, value):
    page.get_by_label(title, exact=False).fill(value)


def attach(page, title, filename, mime, buffer):
    page.get_by_label(title, exact=False).set_input_files(
        {"name": filename, "mimeType": mime, "buffer": buffer}
    )


def drive_application(page):
    page.route(
        "**/api/places?*",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({
                "status": "OK",
                "predictions": [
                    {
                        "description": "Staging Road, Westminster, London SW1A 1AA, UK",
                        "place_id": "ci-synthetic-places-only",
                    }
                ],
            }),
        ),
    )
    page.goto(WEB + "/en/auth?captain=true", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Apply to drive with ACT")).to_be_visible(timeout=30000)
    print("PASS 1/8: ACT single-form driver application loads in mobile Chromium")

    fill(page, "First name", "Staging")
    fill(page, "Last name", "Applicant")
    fill(page, "Date of birth", "1990-04-12")
    fill(page, "UK mobile", "+447700900123")
    fill(page, "Email", EMAIL)
    fill(page, "Postcode", "SW1A 1AA")
    fill(page, "Current UK address", "Staging Road")
    suggestion = page.get_by_role("button", name="Staging Road, Westminster, London SW1A 1AA, UK")
    expect(suggestion).to_be_visible(timeout=10000)
    suggestion.click()
    page.get_by_role("button", name="Continue").click()
    expect(page.get_by_label("TfL PHV driver badge number")).to_be_visible()
    print("PASS 2/8: Google Places suggestion and mobile personal details")

    fill(page, "TfL PHV driver badge number", "SYNTHETIC-PHV-12345")
    fill(page, "TfL badge expiry", future_date(500))
    page.get_by_label("Years of driving experience").select_option("5_plus")
    for title, name in (
        ("TfL PHV badge — front", "pco-front.pdf"),
        ("TfL PHV badge — back", "pco-back.pdf"),
        ("DVLA driving licence — front", "dvla-front.pdf"),
        ("DVLA driving licence — back", "dvla-back.pdf"),
    ):
        attach(page, title, name, "application/pdf", synthetic_pdf())
    attach(page, "Driver photograph", "driver-synthetic.png", "image/png", synthetic_photo())
    page.get_by_role("button", name="Continue").click()
    expect(page.get_by_label("Vehicle ownership")).to_be_visible()
    print("PASS 3/8: Required synthetic identity evidence uploaded in one form")

    page.get_by_label("Vehicle ownership").select_option("phv_owner")
    fill(page, "Vehicle make", "Volkswagen")
    fill(page, "Vehicle model", "Passat")
    fill(page, "Vehicle year", "2025")
    page.get_by_label("ACT vehicle class").select_option("comfort")
    fill(page, "Vehicle registration", "ZZ99 CI1")
    fill(page, "Vehicle colour", "Grey")
    fill(page, "MOT expiry", future_date(400))
    fill(page, "Insurance expiry", future_date(380))
    page.get_by_label("Accepts pets?").select_option("false")
    for title, name in (
        ("MOT certificate", "mot.pdf"),
        ("Valid vehicle insurance", "insurance.pdf"),
        ("Vehicle PHV licence", "vehicle-phv.pdf"),
        ("V5C logbook", "v5c.pdf"),
    ):
        attach(page, title, name, "application/pdf", synthetic_pdf())
    page.get_by_role("button", name="Continue").click()
    expect(page.get_by_text("Review your application before submitting.")).to_be_visible()
    page.get_by_label("I confirm the information is genuine").check()
    page.get_by_label("I understand ACT must check my DBS status").check()
    page.get_by_label("I understand my verified first name").check()
    page.get_by_role("button", name="Submit application").click()
    expect(page.get_by_role("heading", name="Application received")).to_be_visible(timeout=25000)
    summary = page.locator("section").filter(has=page.get_by_role("heading", name="Application received")).inner_text()
    match = re.search(r"Reference #(\d+)", summary)
    assert match, "No unified onboarding reference was shown"
    print("PASS 4/8: Single vehicle/consent submission created one pending application")
    return int(match.group(1))


def acceptance():
    assert os.environ.get("ACT_E2E_ISOLATED") == "1", "Never run against a non-isolated environment"
    assert API == "http://127.0.0.1:8000" and WEB == "http://127.0.0.1:3001"
    status, admin = request_json(
        "POST",
        "/api/auth/login/",
        {"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "account_type": "normal"},
    )
    assert status == 200 and admin.get("access_token"), ("Isolated admin login", status)
    admin_token = admin["access_token"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        applicant = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="en-GB",
            accept_downloads=True,
        )
        applicant_page = applicant.new_page()
        application_id = drive_application(applicant_page)

        detail_url = f"/api/drivers/admin/unified-applications/{application_id}/"
        unauth = applicant.request.get(API + detail_url)
        assert unauth.status in (401, 403), unauth.status
        status, denied = request_json(
            "POST",
            f"/api/drivers/admin/unified-applications/{application_id}/decision/",
            {
                "action": "approve",
                "documents_reviewed": True,
                "dbs_cleared": True,
                "photo_disclosure_consent": True,
            },
            admin_token,
        )
        assert status == 400, (status, denied)
        print("PASS 5/8: Unauthenticated private review denied; approval before password blocked")

        link = find_welcome_link()  # Not logged: this contains a one-time token.
        applicant_page.goto(link, wait_until="domcontentloaded")
        expect(applicant_page.get_by_role("heading", name="ACT Driver — Set your password")).to_be_visible()
        fill(applicant_page, "Password", PASSWORD)
        fill(applicant_page, "Confirm password", PASSWORD)
        applicant_page.get_by_role("button", name="Set up password").click()
        expect(applicant_page.get_by_text("Password set. Your application is still pending ACT verification.")).to_be_visible(timeout=20000)
        status, driver = request_json(
            "POST",
            "/api/drivers/login/",
            {"email": EMAIL, "password": PASSWORD},
        )
        assert status == 200 and driver["user"]["is_admin_verified"] is False, (status, driver)
        assert driver["onboarding_status"]["submission_mode"] == "unified", driver["onboarding_status"]
        status, _ = request_json("GET", "/api/driver/trips/", bearer=driver["access_token"])
        assert status == 403, "Unapproved applicants must not receive trips"
        print("PASS 6/8: Real MailHog email link, password activation and pending-driver trip denial")

        dashboard = browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="en-GB",
            accept_downloads=True,
        )
        dashboard.add_cookies([
            {"url": WEB, "name": "userToken", "value": admin_token},
            {"url": WEB, "name": "account_type", "value": "normal"},
        ])
        admin_page = dashboard.new_page()
        admin_page.goto(WEB + "/en/dashboard/driver-onboarding", wait_until="domcontentloaded")
        expect(admin_page.get_by_text(EMAIL, exact=False).first).to_be_visible(timeout=30000)
        admin_page.get_by_role("button", name="View Details").first.click()
        admin_page.get_by_role("button", name="Review unified application and private evidence").click()
        modal = admin_page.get_by_role("dialog", name="Unified driver application review")
        expect(modal).to_be_visible(timeout=15000)
        expect(modal.get_by_text("Private uploaded evidence")).to_be_visible()
        with admin_page.expect_download(timeout=15000) as download_info:
            modal.get_by_role("button", name="Download").first.click()
        download = download_info.value
        assert download.suggested_filename
        print("PASS 7/8: Mobile admin review opens and streams private evidence with auth")

        modal.get_by_label("I have inspected the genuine identity").check()
        modal.get_by_label("I have independently verified current DBS").check()
        modal.get_by_label("I confirmed consent to disclose").check()
        modal.get_by_role("button", name="Final approve").click()
        expect(modal).to_be_hidden(timeout=15000)
        status, verified = request_json("GET", detail_url, bearer=admin_token)
        assert status == 200 and verified["status"] == "final_approved", (status, verified.get("status"))
        status, trips = request_json("GET", "/api/driver/trips/", bearer=driver["access_token"])
        assert status == 200, (status, trips)
        print("PASS 8/8: Admin approval creates eligible driver, no booking or payment performed")
        dashboard.close()
        applicant.close()
        browser.close()

    print("ACCEPTED: Isolated ACT unified driver browser/API/SMTP journey. NO PRODUCTION CONNECTIONS.")


if __name__ == "__main__":
    acceptance()
