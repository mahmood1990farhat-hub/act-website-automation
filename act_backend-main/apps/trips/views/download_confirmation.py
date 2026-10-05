from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET

from apps.trips.models import Trip


@require_GET
def download_booking_confirmation(request, token):
    """Bearer-token download for a paid booking confirmation PDF."""
    trip = (
        Trip.objects.filter(
            booking_confirmation_token=token,
            is_paid=True,
        )
        .only("id", "booking_confirmation_pdf")
        .first()
    )
    if not trip or not trip.booking_confirmation_pdf:
        raise Http404("Booking confirmation is not available")

    try:
        file_handle = trip.booking_confirmation_pdf.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Booking confirmation is not available")

    response = FileResponse(
        file_handle,
        content_type="application/pdf",
        as_attachment=True,
        filename=f"ACT-booking-{trip.id}.pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
