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


def _money(value):
    try:
        return f"£{float(value):.2f}"
    except (TypeError, ValueError):
        return "£0.00"


def generate_booking_confirmation_pdf(trip, payment_method="Card Payment"):
    """
    Generate booking confirmation PDF from HTML template.
    Returns a BytesIO buffer.
    """
    passenger_name = "N/A"
    if trip.passenger and trip.passenger.user:
        full_name = f"{trip.passenger.user.first_name} {trip.passenger.user.last_name}".strip()
        passenger_name = full_name or trip.passenger.user.username

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
    context = {
        "booking_ref": f"ACT-{trip.stripe_payment_intent}",
        "passenger_name": passenger_name,
        "passengers_count": str(trip.passengers_count or 1),
        "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
        "amount_paid": _money(trip.cost),
        "pickup": trip.pickup_str or f"{trip.pickup_lat}, {trip.pickup_lng}",
        "dropoff": trip.dropoff_str or f"{trip.dropoff_lat}, {trip.dropoff_lng}",
        "trip_date": trip.trip_date.strftime("%d %B %Y"),
        "trip_time": trip.trip_time.strftime("%I:%M%p").lower(),
        "trip_cost": _money(trip.base_trip_cost or trip.cost),
        "vat_20": _money((trip.regular_vat or 0) + (trip.airport_vat or 0)),
        "total_cost": _money(trip.cost),
        "payment_method": payment_method,
        "logo_uri": Path(logo_path).as_uri() if os.path.exists(logo_path) else "",
        "footer_logo_uri": Path(footer_logo_path).as_uri() if os.path.exists(footer_logo_path) else "",
        "booking": {
            "reference": trip.stripe_payment_intent,
            "passenger_name": passenger_name,
            "passengers_count": str(trip.passengers_count or 1),
            "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
            "amount_paid": f"{float(trip.cost or 0):.2f}",
            "pickup_location": trip.pickup_str or f"{trip.pickup_lat}, {trip.pickup_lng}",
            "dropoff_location": trip.dropoff_str or f"{trip.dropoff_lat}, {trip.dropoff_lng}",
            "pickup_date": trip.trip_date.strftime("%d %B %Y"),
            "pickup_time": trip.trip_time.strftime("%I:%M%p").lower(),
            "trip_cost": f"{float(trip.base_trip_cost or trip.cost or 0):.2f}",
            "vat_amount": f"{float((trip.regular_vat or 0) + (trip.airport_vat or 0)):.2f}",
            "total_amount": f"{float(trip.cost or 0):.2f}",
            "payment_method": payment_method,
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
    passenger_name = "N/A"
    if trip.passenger and trip.passenger.user:
        full_name = f"{trip.passenger.user.first_name} {trip.passenger.user.last_name}".strip()
        passenger_name = full_name or trip.passenger.user.username

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
        "payment_title": "Payment Summery",
        "booking": {
            "reference": trip.stripe_payment_intent,
            "passenger_name": passenger_name,
            "passengers_count": str(trip.passengers_count or 1),
            "vehicle_name": trip.car_type.name_en if trip.car_type else "N/A",
            "amount_paid": f"{float(trip.cost or 0):.2f}",
            "pickup_location": trip.pickup_str or f"{trip.pickup_lat}, {trip.pickup_lng}",
            "dropoff_location": trip.dropoff_str or f"{trip.dropoff_lat}, {trip.dropoff_lng}",
            "pickup_date": trip.trip_date.strftime("%d %B %Y"),
            "pickup_time": trip.trip_time.strftime("%I:%M%p").lower(),
            "trip_cost": f"{float(trip.base_trip_cost or trip.cost or 0):.2f}",
            "vat_amount": f"{float((trip.regular_vat or 0) + (trip.airport_vat or 0)):.2f}",
            "total_amount": f"{float(trip.cost or 0):.2f}",
            "payment_method": payment_method,
        },
    }

    html = render_to_string("pdf/booking_confirmation.html", context)
    buffer = BytesIO()
    HTML(string=html, base_url=settings.BASE_DIR).write_pdf(target=buffer)
    buffer.seek(0)
    return buffer

