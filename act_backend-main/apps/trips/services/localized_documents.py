"""Customer documents use the booking's language, never a webhook/staff locale.

Only ACT-authored labels and enumerated choices are translated. Passenger names,
addresses, airline names, notes and other user/provider content stay verbatim.
"""
from functools import lru_cache
import json
from pathlib import Path

from django.template.loader import render_to_string

from .booking_details_formatter import format_booking_details_for_email
from .customer_language import booking_language
from .customer_documents import render_arabic_document

DOCUMENT_LOCALES = ("fr", "de", "es", "tr", "zh-CN")
KINDS = ("booking", "cancellation", "driver", "driver_cancelled", "reassigned")
CHOICES = {
    "Not provided": "not_provided", "Not applicable": "not_applicable",
    "Not required": "not_required", "Not selected": "not_selected", "None": "none",
    "Yes": "yes", "No": "no", "Arrival": "arrival", "Departure": "departure",
    "Landing Time": "landing_time", "Departure Time": "departure_time", "Time": "flight_time",
    "N/A": "not_available", "Private Transfer": "private_transfer",
    "External Driver": "external_driver", "Assigned Driver": "assigned_driver",
    "I will provide my own infant seats": "own_infant",
    "I would like ACT to provide infant seats": "request_infant",
    "I understand ACT may not have infant seats available and wish to continue": "unavailable_infant",
    "I will provide my own child seats": "own_child",
    "I would like ACT to provide child seats": "request_child",
    "I understand ACT may not have child seats available and wish to continue": "unavailable_child",
}


@lru_cache(maxsize=5)
def document_catalog(locale):
    if locale not in DOCUMENT_LOCALES:
        raise ValueError("Unsupported document locale")
    return json.loads((Path(__file__).parent / "document_locales" / (locale + ".json")).read_text(encoding="utf-8"))


def localized_document_context(trip, kind, refund_message="", driver=None, download_url="", logo_uri="", payment_method="Card Payment", font_uri=""):
    locale = booking_language(trip)
    if kind not in KINDS:
        raise ValueError("Unsupported document kind")
    labels = document_catalog(locale)
    details = format_booking_details_for_email(trip)
    raw = getattr(trip, "booking_details", None)
    raw = raw if isinstance(raw, dict) else {}
    flight_raw = raw.get("flight_details")
    flight_raw = flight_raw if isinstance(flight_raw, dict) else {}
    extra_raw = raw.get("additional_requirements")
    extra_raw = extra_raw if isinstance(extra_raw, dict) else {}
    user = getattr(getattr(trip, "passenger", None), "user", None)
    name = getattr(trip, "passenger_name", "") or (user.get_full_name() if user else "") or labels["passenger_fallback"]
    car = getattr(trip, "car_type", None)
    def choice(value):
        return labels[CHOICES[str(value)]] if str(value) in CHOICES else str(value)
    def customer_field(key):
        value = flight_raw.get(key)
        return str(value) if value is not None and str(value).strip() else labels["not_applicable"]
    def location(prefix):
        return getattr(trip, prefix + "_str", "") or f'{getattr(trip, prefix + "_lat", "")}, {getattr(trip, prefix + "_lng", "")}'
    rows = []
    def add(key, value):
        rows.append((labels[key], value))
    add("reference", f"ACT-{int(trip.id):06d}")
    add("passenger", name)
    vehicle_name = getattr(car, "name_en", None) or ""
    vehicle_code = getattr(car, "code", None) or ""
    vehicle_code_keys = {"comfort": "standardVehicle", "comfort_xl": "sevenSeater", "executive": "luxuryVehicle", "executive_xl": "luxuryVan", "first_class": "executiveVehicle"}
    vehicle_keys = {"standard phv": "standardVehicle", "standard car": "standardVehicle", "saloon": "standardVehicle", "7 seaters phv": "sevenSeater", "7 seater": "sevenSeater", "7 seaters": "sevenSeater", "luxury": "luxuryVehicle", "luxury van": "luxuryVan", "vip business phv": "executiveVehicle", "executive": "executiveVehicle", "comfort class": "standardVehicle", "comfort xl": "sevenSeater", "executive class": "luxuryVehicle", "executive xl": "luxuryVan", "first class": "executiveVehicle"}
    vehicle_key = vehicle_code_keys.get(vehicle_code) or vehicle_keys.get(vehicle_name.strip().lower())
    add("vehicle", labels[vehicle_key] if vehicle_key else vehicle_name or labels["private_transfer"])
    add("pickup", location("pickup")); add("dropoff", location("dropoff"))
    # ISO date and 24-hour pickup time are unambiguous for international guests.
    add("date", trip.trip_date.isoformat()); add("time", trip.trip_time.strftime("%H:%M"))
    add("cost", f"GBP {trip.cost:.2f}")
    for key in ("adults", "children", "infants"):
        add(key, details["passenger_counts"][key])
    add("total_passengers", details["passenger_counts"]["total"])
    flight = details["flight_details"]
    add("flight_type", choice(flight["type"]))
    add("flight_number", customer_field("flight_number")); add("airline", customer_field("airline"))
    rows.append((choice(flight["time_label"]), choice(flight["time"])))
    add("sign", customer_field("pickup_sign_name"))
    add("infant_seat", choice(details["child_infant_travel"]["infant_seat_option"]))
    add("child_seat", choice(details["child_infant_travel"]["child_seat_option"]))
    add("meet_greet", choice(details["additional_requirements"]["meet_and_greet"]))
    add("wheelchair", choice(details["additional_requirements"]["foldable_wheelchair"]))
    add("notes", extra_raw.get("notes_to_driver") or labels["none"])
    add("extras", details["extra_services"] if raw.get("extra_services") else labels["none"])
    if kind in ("booking", "cancellation"):
        add("fare", f'GBP {getattr(trip, "base_trip_cost", None) or trip.cost:.2f}')
        add("uplift", f'GBP {getattr(trip, "regular_vat", None) or 0:.2f}')
        if getattr(trip, "airport_vat", None):
            add("airport_fee", f'GBP {trip.airport_vat:.2f}')
        if getattr(trip, "min_adjustment", None):
            add("minimum_adjustment", f'GBP {trip.min_adjustment:.2f}')
        add("total", f"GBP {trip.cost:.2f}")
        add("payment_method", labels["card_payment"] if payment_method == "Card Payment" else payment_method)
        if getattr(trip, "card_brand", None):
            add("card", f'{trip.card_brand} ****{getattr(trip, "last4", "") or ""}')
    driver = driver or {}
    for field, key in (("name", "driver_name"), ("phone", "driver_phone"), ("company", "company"),
                       ("vehicle", "vehicle"), ("registration", "registration"), ("color", "color")):
        if driver.get(field): add(key, driver[field])
    refunds = {
        "Your payment has been refunded to your original payment method.": "refund_done",
        "No card payment was refunded for this booking.": "refund_none",
    }
    return dict(locale=locale, title=labels[kind + "_title"], intro=labels[kind + "_intro"], rows=rows,
                labels=labels, contact=labels["contact"], logo_uri=logo_uri, font_uri=font_uri,
                website_url="https://airportandcitytransfer.com/" + locale,
                refund_message=labels[refunds.get(refund_message, "refund_unknown")] if refund_message else "",
                download_url=download_url, driver_pco_url=driver.get("pco_url", ""))


def render_customer_document(trip, kind, **kwargs):
    if booking_language(trip) == "ar":
        kwargs.pop("payment_method", None)
        kwargs.pop("font_uri", None)
        return render_arabic_document(trip, kind, **kwargs)
    context = localized_document_context(trip, kind, **kwargs)
    html = render_to_string("customer/localized_confirmation.html", context)
    text = "\n\n".join([context["title"], context["intro"], context["refund_message"],
                         "\n".join(f"{key}: {value}" for key, value in context["rows"]),
                         context["contact"], context["website_url"]])
    for url in (context["download_url"], context["driver_pco_url"]):
        if url: text += "\n" + url
    return f'{context["title"]} – ACT-{int(trip.id):06d}', html, text
