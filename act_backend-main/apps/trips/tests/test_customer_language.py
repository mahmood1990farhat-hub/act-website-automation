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
from apps.trips.services.customer_language import booking_language, details_with_language, normalize_language, use_booking_language
from apps.trips.services.customer_documents import render_arabic_document
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
    names = {"_send_arabic_customer_email", "_format_booking_details_text", "_booking_reference",
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
    def test_english_driver_registration(self):
        html = render_to_string("emails/trip_driver_details_passenger.html", {"vehicle_registration": "TEST123"})
        self.assertIn("TEST123", html)
        self.assertNotIn("{{ vehicle_registration", html)

    def test_language_allowlist_and_legacy(self):
        self.assertEqual(normalize_language("AR-eg"), "ar")
        self.assertEqual(normalize_language("fr"), "en")
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
