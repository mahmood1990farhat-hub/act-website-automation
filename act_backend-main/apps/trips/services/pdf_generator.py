from io import BytesIO
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML

from apps.trips.services.booking_details_formatter import format_booking_details_for_email
from utils.common.google_map import place_to_string


def _money(value):
    try:
        return f"£{float(value):.2f}"
    except (TypeError, ValueError):
        return "£0.00"


def _booking_reference(trip):
    return f"ACT-{int(trip.id):06d}"


def _payment_method_label(trip, fallback="Card Payment"):
    if trip.card_brand and trip.last4:
        return f"{fallback} ({trip.card_brand} ********{trip.last4})"
    return fallback


def _readable_location(place_id, stored_location, lat, lng):
    if stored_location:
        return stored_location

    place_label = place_to_string(place_id)
    if place_label:
        return place_label

    return f"{lat}, {lng}"


def _passenger_name(trip):
    snapshot_name = (getattr(trip, "passenger_name", "") or "").strip()
    if snapshot_name:
        return snapshot_name

    user = getattr(getattr(trip, "passenger", None), "user", None)
    if user:
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name or user.username or "Passenger"

    return "Passenger"


def generate_booking_confirmation_pdf(trip, payment_method="Card Payment"):
    """
    Generate booking confirmation PDF from HTML template.
    Returns a BytesIO buffer.
    """
    passenger_name = _passenger_name(trip)

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "assets",
        "act_logo.png",
    )
    footer_logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "email-assets",
        "trip_accepted",
        "footer-logo.png",
    )
    booking_ref = _booking_reference(trip)
    payment_method_label = _payment_method_label(trip, payment_method)
    pickup_location = _readable_location(
        trip.pickup_place_id,
        trip.pickup_str,
        trip.pickup_lat,
        trip.pickup_lng,
    )
    dropoff_location = _readable_location(
        trip.dropoff_place_id,
        trip.dropoff_str,
        trip.dropoff_lat,
        trip.dropoff_lng,
    )

    context = {
        "booking_ref": booking_ref,
        "confirmation_title": "Your Booking Confirmation",
        "reference_label": "Reference Number",
        "intro_title": "Dear Customer",
        "intro_text": (
            "Thank you for choosing Airport and City Transfer. "
            "Your journey has been successfully confirmed. Please take a moment to "
            "review your booking details and keep this confirmation for reference. We "
            "look forward to delivering a seamless and premium travel experience."
        ),
        "booking_details_title": "Your Booking Details",
        "journey_title": "JOURNEY",
        "payment_title": "Payment Summary",
        "passenger_name": passenger_name,
        "passengers_count": str(trip.passengers_count or 1),
        "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
        "amount_paid": _money(trip.cost),
        "pickup": pickup_location,
        "dropoff": dropoff_location,
        "trip_date": trip.trip_date.strftime("%d %B %Y"),
        "trip_time": trip.trip_time.strftime("%I:%M%p").lower(),
        "trip_cost": _money(trip.base_trip_cost or trip.cost),
        "vat_20": _money((trip.regular_vat or 0) + (trip.airport_vat or 0)),
        "total_cost": _money(trip.cost),
        "payment_method": payment_method_label,
        "booking_details": format_booking_details_for_email(trip),
        "logo_uri": Path(logo_path).as_uri() if os.path.exists(logo_path) else "",
        "footer_logo_uri": Path(footer_logo_path).as_uri() if os.path.exists(footer_logo_path) else "",
        "booking": {
            "reference": booking_ref,
            "passenger_name": passenger_name,
            "passengers_count": str(trip.passengers_count or 1),
            "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
            "amount_paid": f"{float(trip.cost or 0):.2f}",
            "pickup_location": pickup_location,
            "dropoff_location": dropoff_location,
            "pickup_date": trip.trip_date.strftime("%d %B %Y"),
            "pickup_time": trip.trip_time.strftime("%I:%M%p").lower(),
            "trip_cost": f"{float(trip.base_trip_cost or trip.cost or 0):.2f}",
            "vat_amount": f"{float((trip.regular_vat or 0) + (trip.airport_vat or 0)):.2f}",
            "total_amount": f"{float(trip.cost or 0):.2f}",
            "payment_method": payment_method_label,
        },
    }

    html = render_to_string("pdf/booking_confirmation.html", context)
    buffer = BytesIO()
    HTML(string=html, base_url=settings.BASE_DIR).write_pdf(target=buffer)
    buffer.seek(0)
    return buffer


def generate_cancellation_confirmation_pdf(trip, payment_method="Card Payment"):
    """
    Generate cancellation confirmation PDF from HTML template.
    Returns a BytesIO buffer.
    """
    passenger_name = _passenger_name(trip)

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "assets",
        "act_logo.png",
    )
    footer_logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "email-assets",
        "trip_accepted",
        "footer-logo.png",
    )
    booking_ref = _booking_reference(trip)
    payment_method_label = _payment_method_label(trip, payment_method)
    pickup_location = _readable_location(
        trip.pickup_place_id,
        trip.pickup_str,
        trip.pickup_lat,
        trip.pickup_lng,
    )
    dropoff_location = _readable_location(
        trip.dropoff_place_id,
        trip.dropoff_str,
        trip.dropoff_lat,
        trip.dropoff_lng,
    )

    context = {
        "logo_uri": Path(logo_path).as_uri() if os.path.exists(logo_path) else "",
        "footer_logo_uri": Path(footer_logo_path).as_uri() if os.path.exists(footer_logo_path) else "",
        "confirmation_title": "Your Cancellation Confirmation",
        "reference_label": "Reference Number",
        "intro_title": "Dear Customer",
        "intro_text": (
            "We confirm that your booking has been successfully cancelled. "
            "If you are eligible for a refund, it will be processed to your original payment method. "
            "To make a new booking, please visit airportandcitytransfer.com."
        ),
        "booking_details_title": "Your Booking Details",
        "journey_title": "JOURNEY",
        "payment_title": "Payment Summary",
        "booking_details": format_booking_details_for_email(trip),
        "booking": {
            "reference": booking_ref,
            "passenger_name": passenger_name,
            "passengers_count": str(trip.passengers_count or 1),
            "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
            "amount_paid": f"{float(trip.cost or 0):.2f}",
            "pickup_location": pickup_location,
            "dropoff_location": dropoff_location,
            "pickup_date": trip.trip_date.strftime("%d %B %Y"),
            "pickup_time": trip.trip_time.strftime("%I:%M%p").lower(),
            "trip_cost": f"{float(trip.base_trip_cost or trip.cost or 0):.2f}",
            "vat_amount": f"{float((trip.regular_vat or 0) + (trip.airport_vat or 0)):.2f}",
            "total_amount": f"{float(trip.cost or 0):.2f}",
            "payment_method": payment_method_label,
        },
    }

    html = render_to_string("pdf/booking_confirmation.html", context)
    buffer = BytesIO()
    HTML(string=html, base_url=settings.BASE_DIR).write_pdf(target=buffer)
    buffer.seek(0)
    return buffer

