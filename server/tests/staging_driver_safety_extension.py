"""Exercise suspension -> permanent cessation after the existing isolated journey.

Uses the same synthetic applicant; never creates another real booking or payment.
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "act_website-main/tests"))
from staging_tfl_operator_journey import (
    acceptance, request_json, API, WEB, EMAIL, PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD,
)
from playwright.sync_api import sync_playwright, expect


def run():
    assert os.environ.get("ACT_E2E_ISOLATED") == "1"
    assert API == "http://127.0.0.1:8000" and WEB == "http://127.0.0.1:3001"
    acceptance()
    status, admin = request_json("POST", "/api/auth/login/", {
        "username": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "account_type": "normal",
    })
    assert status == 200
    token = admin["access_token"]
    status, driver = request_json("POST", "/api/drivers/login/", {"email": EMAIL, "password": PASSWORD})
    assert status == 200
    uid = driver["user"]["id"]
    status, listing = request_json("GET", "/api/drivers/admin/onboarding-requests/", bearer=token)
    assert status == 200
    matches = [r for r in listing["data"] if r.get("email_address") == EMAIL or r.get("user_email") == EMAIL]
    assert len(matches) == 1
    app_id = matches[0]["id"]
    status, _ = request_json("POST", f"/api/admin-panel/users/{uid}/deactivate/", {}, token)
    assert status == 200
    status, _ = request_json("GET", "/api/driver/trips/", bearer=driver["access_token"])
    assert status in (401, 403)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="en-GB")
        ctx.add_cookies([
            {"url": WEB, "name": "userToken", "value": token},
            {"url": WEB, "name": "account_type", "value": "normal"},
        ])
        page = ctx.new_page()
        page.goto(WEB + "/en/dashboard/driver-onboarding", wait_until="domcontentloaded")
        cards = page.locator("div.my-5.xl\\:hidden")
        expect(cards.get_by_text(EMAIL, exact=True)).to_be_visible(timeout=30000)
        cards.get_by_role("button", name="View Details").first.click()
        page.get_by_role("button", name="Review unified application and private evidence").click()
        modal = page.get_by_role("dialog", name="Unified driver application review")
        expect(modal).to_be_visible(timeout=15000)
        modal.get_by_label("Reason for ceasing driver availability").fill("Synthetic driver permanently leaves ACT")
        modal.get_by_label("I have reviewed all current assignments").check()
        page.once("dialog", lambda dialog: dialog.accept())
        modal.get_by_role("button", name="End ACT availability", exact=True).click()
        expect(modal).to_be_hidden(timeout=15000)
        ctx.close()
        browser.close()
    status, detail = request_json("GET", f"/api/drivers/admin/unified-applications/{app_id}/", bearer=token)
    assert status == 200
    assert detail["operator_record"]["driver_ceased_available_on"]
    assert detail["vehicle_history"][0]["ceased_at"]
    status, _ = request_json("POST", f"/api/admin-panel/users/{uid}/activate/", {}, token)
    assert status == 409
    print("ACCEPTED: suspended driver can be permanently ceased in mobile admin; old activation cannot revive availability.")


if __name__ == "__main__":
    run()
