"""Offline checks: no database, Stripe, Google Maps, or outgoing email."""
import ast
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS
import logging
import re
import unittest
from urllib.parse import quote
from typing import Optional
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext as _, override, get_language

BASE = Path(__file__).resolve().parents[3]
if not settings.configured:
    settings.configure(BASE_DIR=str(BASE), SECRET_KEY="offline-test", USE_I18N=True,
                       TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates",
                                   "DIRS": [str(BASE / "apps/trips/templates")], "APP_DIRS": False}])
    import django
    django.setup()
from apps.trips.services.customer_language import booking_language, details_with_language, normalize_language, use_booking_language, use_internal_language
from apps.trips.services.customer_documents import render_arabic_document
from apps.trips.services.localized_documents import render_customer_document, document_catalog, DOCUMENT_LOCALES
from apps.accounts.customer_messages import account_message
from apps.trips.services.booking_details_formatter import format_booking_details_for_email


def sample(language="ar"):
    user = NS(id=1, email="preview@example.invalid", first_name="ليلى", get_full_name=lambda: "ليلى Test")
    return NS(id=42, booking_details=details_with_language({
        "passenger_counts": {"adults": 2, "children": 1, "infants": 1, "total": 4},
        "flight_details": {"flight_type": "arrival", "flight_number": "BA123", "airline": "British Airways", "landing_time": "10:00"},
        "child_infant_travel": {"infant_seat_option": "I will provide my own infant seats", "child_seat_option": "I would like ACT to provide child seats"},
        "additional_requirements": {"meet_and_greet": True, "notes_to_driver": "<script>alert(1)</script> ملاحظة"},
    }, language), passenger=NS(user=user), passenger_name="ليلى Test", passenger_email=user.email,
        passenger_country_code="+44", passenger_phone="0000", passengers_count=4,
        car_type=NS(name_en="Saloon", name_ar="سيارة صالون"), trip_date=date(2026,10,9), trip_time=time(10,30),
        pickup_str="Heathrow Terminal 5", dropoff_str="London شارع",
        pickup_lat=51, pickup_lng=0, dropoff_lat=51, dropoff_lng=0,
        pickup_place_id=None, dropoff_place_id=None, cost=Decimal("120"),
        base_trip_cost=Decimal("100"), regular_vat=Decimal("20"), airport_vat=Decimal("0"),
        card_brand="Visa", last4="4242", booking_confirmation_pdf=None, cancellation_confirmation_pdf=None,
        base_driver=None)


def email_functions(captured):
    # Execute real production function bodies with only external side effects substituted.
    source = ast.parse((BASE / "utils/common/email.py").read_text())
    names = {"_send_localized_customer_email", "send_passenger_registration_confirmation", "send_password_reset_otp", "_format_booking_details_text", "_booking_reference",
             "_dial_code_only", "_format_passenger_phone", "send_passenger_confirmation",
             "send_passenger_trip_cancellation_to_passenger", "send_trip_accepted_to_passenger",
             "send_driver_cancellation_to_passenger", "send_trip_reassigned_to_passenger"}
    module = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
    env = dict(globals(), logger=logging.getLogger("offline"), settings=settings,
               _send_mail_async=lambda *a, **kw: captured.append((a, kw)),
               _email_asset_url=lambda p: "https://assets.example.invalid/" + p, _absolute_app_url=lambda p: p,
               _trip_locations_for_email=lambda t: (t.pickup_str,t.dropoff_str), place_to_string=lambda p: None)
    exec(compile(module, str(BASE / "utils/common/email.py"), "exec"), env)
    return env


class CustomerLanguageTests(unittest.TestCase):
    def test_verification_provider_receives_explicit_language(self):
        calls = []
        service = NS(verifications=NS(create=lambda **kw: (calls.append(kw) or NS(status="pending"))))
        source = ast.parse((BASE / "utils/common/twilio_verify.py").read_text())
        fn = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "send_verification_code")
        env = {"client": NS(verify=NS(v2=NS(services=lambda sid: service))), "settings": NS(TWILIO_VERIFY_SERVICE_SID="offline"), "normalize_language": normalize_language}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "twilio_verify.py", "exec"), env)
        for locale in ("en", "ar", "fr", "de", "es", "tr", "zh-CN"):
            self.assertEqual(env["send_verification_code"]("+447700900000", locale=locale), "pending")
            self.assertEqual(calls[-1], {"to": "+447700900000", "channel": "sms", "locale": locale})
        env["send_verification_code"]("+447700900000")
        self.assertNotIn("locale", calls[-1])

    def test_customer_download_links_use_the_correct_stored_pdf(self):
        captured = []; env = email_functions(captured)
        for locale in ("en", "ar", *DOCUMENT_LOCALES):
            trip = sample(locale)
            trip.booking_confirmation_pdf = NS(url=f"/media/{locale}/booking.pdf")
            trip.cancellation_confirmation_pdf = NS(url=f"/media/{locale}/cancellation.pdf")
            for function, expected, wrong in (
                ("send_passenger_confirmation", "booking.pdf", "cancellation.pdf"),
                ("send_passenger_trip_cancellation_to_passenger", "cancellation.pdf", "booking.pdf"),
            ):
                before = len(captured)
                with override("tr" if locale != "tr" else "ar"):
                    env[function](trip.passenger.user, trip)
                self.assertEqual(len(captured), before + 1)
                html = captured[-1][1]["html_message"]
                self.assertIn(f"/media/{locale}/{expected}", html)
                self.assertNotIn(f"/media/{locale}/{wrong}", html)

    def test_internal_notifications_are_always_english(self):
        from datetime import datetime, timezone
        from django.utils import timezone as django_timezone
        source = ast.parse((BASE / "utils/common/email.py").read_text())
        names = {"send_internal_notification", "send_trip_accepted_to_admin",
                 "send_passenger_trip_cancellation_to_admin", "send_driver_cancellation_to_admin",
                 "_format_booking_details_text", "_format_trip_luggage_label", "_booking_reference",
                 "_dial_code_only", "_format_passenger_phone"}
        module = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        captured = []
        def send(*args, **kwargs):
            self.assertEqual(get_language(), "en")
            captured.append((args, kwargs))
        env = dict(globals(), logger=logging.getLogger("offline-internal"), django_timezone=django_timezone,
                   _send_mail_async=send, _trip_locations_for_email=lambda t:(t.pickup_str,t.dropoff_str),
                   place_to_string=lambda _:None, _email_asset_url=lambda _:"", settings=NS(ADMIN_EMAIL="owner@example.invalid"))
        exec(compile(module, "internal_email_production", "exec"), env)
        for locale in ("en", "ar", *DOCUMENT_LOCALES):
            trip = sample(locale)
            trip.created_at = datetime(2026,10,3,tzinfo=timezone.utc)
            trip.is_paid=True; trip.stripe_payment_intent="pi_synthetic"; trip.large_suitcase=1; trip.small_suitcase=1
            trip.cancelled_at = trip.created_at
            trip.status="cancelled"; trip.cancellation_reason="Original customer text"
            for function, extra, subject in (
                ("send_internal_notification", (), "New Booking Received"),
                ("send_trip_accepted_to_admin", (None,), "Trip confirmed by driver"),
                ("send_passenger_trip_cancellation_to_admin", (), "Passenger cancelled trip"),
                ("send_driver_cancellation_to_admin", (), "Driver Cancelled Trip"),
            ):
                before = len(captured)
                with override(locale):
                    env[function](trip, *extra)
                    self.assertEqual(get_language(), locale.lower())
                self.assertEqual(len(captured), before+1, function)
                self.assertIn(subject, captured[-1][0][0])
                self.assertEqual(captured[-1][0][2], ["owner@example.invalid"])
                self.assertIn("Heathrow Terminal 5", captured[-1][0][1])

    def test_all_new_locales_dispatch_from_booking(self):
        captured = []
        env = email_functions(captured)
        for locale in DOCUMENT_LOCALES:
            trip = sample(locale)
            with override("ar"):
                for function, kind in (("send_passenger_confirmation", "booking"),
                                       ("send_passenger_trip_cancellation_to_passenger", "cancellation"),
                                       ("send_driver_cancellation_to_passenger", "driver_cancelled")):
                    before = len(captured)
                    env[function](trip.passenger.user, trip)
                    self.assertEqual(len(captured), before + 1, (locale, function))
                    args, kwargs = captured[-1]
                    self.assertIn(document_catalog(locale)[kind + "_title"], args[0])
                    self.assertIn(f'lang="{locale}" dir="ltr"', kwargs["html_message"])
                    self.assertIn("/" + locale, args[1])
                    self.assertEqual(args[2], [trip.passenger_email])
                driver = {"name": "张伟 <Driver>", "phone": "+4412345", "company": "Partner",
                          "car": {"brand_model": "Mercedes", "registration_number": "AB12"}}
                for function in ("send_trip_accepted_to_passenger", "send_trip_reassigned_to_passenger"):
                    before = len(captured)
                    env[function](trip.passenger.user, trip, is_guest_driver=True, guest_driver_info=driver)
                    self.assertEqual(len(captured), before + 1, (locale, function))
                    args, kwargs = captured[-1]
                    self.assertIn(f'lang="{locale}"', kwargs["html_message"])
                    self.assertIn("张伟 &lt;Driver&gt;", kwargs["html_message"])
                self.assertEqual(get_language(), "ar")

    def test_new_document_content_does_not_translate_user_values(self):
        for locale in DOCUMENT_LOCALES:
            trip = sample(locale)
            trip.passenger_name = "None <Test>"
            trip.booking_details["flight_details"]["airline"] = "Arrival"
            trip.booking_details["flight_details"]["pickup_sign_name"] = "Not provided"
            for kind in ("booking", "cancellation", "driver", "driver_cancelled", "reassigned"):
                _, html, text = render_customer_document(trip, kind, refund_message="unverified provider status")
                self.assertIn("None &lt;Test&gt;", html)
                self.assertIn(">Arrival<", html)
                self.assertIn(">Not provided<", html)
                self.assertIn("Heathrow Terminal 5", html)
                self.assertNotIn("<script>", html)
                self.assertIn("&lt;script&gt;", html)
                self.assertNotIn("unverified provider status", html)
                self.assertIn(document_catalog(locale)["refund_unknown"], text)
                self.assertNotIn("I will provide my own", html)
                self.assertNotIn("<style>", text)

    def test_account_emails_use_explicit_language(self):
        captured = []; env = email_functions(captured)
        user = sample().passenger.user
        for locale in ("en", "ar", *DOCUMENT_LOCALES):
            with override("de" if locale != "de" else "ar"):
                env["send_passenger_registration_confirmation"](user, locale=locale)
                self.assertEqual(captured[-1][0][0], account_message("welcome", user, locale)[0])
                env["send_password_reset_otp"](user, "123456", locale=locale)
                self.assertEqual(captured[-1][0][0], account_message("reset", user, locale)[0])
                self.assertIn("123456", captured[-1][0][1])
                self.assertEqual(captured[-1][0][2], [user.email])

    def test_locale_variants_and_catalog_contract(self):
        for raw, expected in (("zh_CN", "zh-CN"), ("zh-Hans", "zh-CN"), ("zh-Hant", "en"),
                              ("zh-TW", "en"), ("de-DE", "de"), ("fr-FR", "fr"), ("../fr", "en")):
            self.assertEqual(normalize_language(raw), expected)
        keys = set(document_catalog("fr"))
        for locale in DOCUMENT_LOCALES:
            self.assertEqual(set(document_catalog(locale)), keys)
            self.assertTrue(all(isinstance(value, str) and value.strip() for value in document_catalog(locale).values()))

    def test_airport_fee_is_not_presented_as_percentage_uplift(self):
        from apps.trips.services.localized_documents import localized_document_context
        trip = sample("fr")
        trip.airport_vat = Decimal("10")
        trip.min_adjustment = Decimal("5")
        trip.cost = Decimal("135")
        context = localized_document_context(trip, "booking")
        rows = dict(context["rows"])
        labels = document_catalog("fr")
        self.assertEqual(rows[labels["uplift"]], "GBP 20.00")
        self.assertEqual(rows[labels["airport_fee"]], "GBP 10.00")
        self.assertEqual(rows[labels["minimum_adjustment"]], "GBP 5.00")
        self.assertEqual(rows[labels["total"]], "GBP 135.00")

    def test_english_driver_registration(self):
        html = render_to_string("emails/trip_driver_details_passenger.html", {"vehicle_registration": "TEST123"})
        self.assertIn("TEST123", html)
        self.assertNotIn("{{ vehicle_registration", html)

    def test_language_allowlist_and_legacy(self):
        self.assertEqual(normalize_language("AR-eg"), "ar")
        self.assertEqual(normalize_language("fr"), "fr")
        self.assertEqual(booking_language(NS(booking_details=None)), "en")
        original={"flight_details":{"flight_number":"BA123"}}
        pending=details_with_language(original,"ar")
        self.assertNotIn("customer_language",original)
        # Webhook copies pending booking_details onto Trip without re-inferring locale.
        self.assertEqual(booking_language(NS(booking_details=pending)), "ar")

    def test_templates_and_safe_user_data(self):
        for kind in ("booking","cancellation","driver","driver_cancelled","reassigned"):
            _,html,text=render_arabic_document(sample(),kind)
            self.assertIn('lang="ar" dir="rtl"',html)
            self.assertIn("Heathrow Terminal 5",html)
            self.assertNotIn("<script>",html)
            self.assertIn("&lt;script&gt;",html)
            self.assertNotIn("Not applicable",html)
            self.assertNotIn("I will provide",html)
            self.assertIn("/ar",text)
            self.assertNotIn("<style>",text)

    def test_actual_email_paths_are_booking_owned(self):
        captured=[]; env=email_functions(captured)
        for language in ("en","ar"):
            t=sample(language); user=t.passenger.user
            with override("ar" if language=="en" else "en"):
                for fn in ("send_passenger_confirmation","send_passenger_trip_cancellation_to_passenger","send_driver_cancellation_to_passenger"):
                    before=len(captured);env[fn](user,t)
                    self.assertEqual(len(captured),before+1,fn)
                    args,kw=captured[-1]
                    self.assertEqual(args[2],[user.email])
                    if language=="ar":
                        self.assertIn('dir="rtl"',kw["html_message"])
                        self.assertIn('src="https://assets.example.invalid/trip_accepted/footer-logo.png"',kw["html_message"])
                        self.assertIn("/ar",args[1])
                    self.assertEqual(get_language(),"ar" if language=="en" else "en")
                env["send_trip_accepted_to_passenger"](user,t,is_guest_driver=True,guest_driver_info={"name":"Driver","phone":"+44123","car":{"brand_model":"Mercedes","registration_number":"AB12"}})
                if language == "ar":
                    self.assertIn("AB12",captured[-1][1]["html_message"])
                env["send_trip_reassigned_to_passenger"](user,t,True,{"name":"Driver","phone":"+44123","company":"Partner"})
                self.assertIn("Partner",captured[-1][0][1])

    def test_refund_status_not_invented(self):
        _,_,text=render_arabic_document(sample(),"cancellation",refund_message="No card payment was refunded for this booking.")
        self.assertIn("لم يتم رد",text)
        _,_,text=render_arabic_document(sample(),"cancellation",refund_message="unknown internal status")
        self.assertNotIn("unknown internal status",text)
        self.assertIn("للاستفسار",text)


if __name__ == "__main__":
    unittest.main()
