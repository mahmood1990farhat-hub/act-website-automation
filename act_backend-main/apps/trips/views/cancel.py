from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger
from django.utils.translation import gettext as _, activate
from utils.common import get_locale
import stripe
from django.conf import settings
from ..models import Trip
from django.shortcuts import get_object_or_404

from apps.trips.services.trip_tracking import stop_trip_tracking
from apps.trips.services.booking_confirmation import ensure_cancellation_confirmation_pdf
from utils.common.email import (
    send_passenger_trip_cancellation_to_passenger,
    send_passenger_trip_cancellation_to_admin,
)

import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY




class CancelTripView(EMADBaseView):
    permission_classes = [IsPassenger]
    http_method_names = ['post']

    def handle_post(self, request, trip_id):
        activate(get_locale(request=request))
        passenger = request.user.passenger_profile
        trip = get_object_or_404(Trip, id=trip_id, passenger=passenger)

        if trip.status != "pending":
            return self.format_response(
                message=_("Only pending trips can be cancelled."),
                success=False,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if trip.is_paid and trip.stripe_payment_intent:
            try:
                refund = stripe.Refund.create(
                    payment_intent=trip.stripe_payment_intent,
                )
            except stripe.error.StripeError as e:
                return self.format_response(
                    message=_("Failed to process refund"),
                    data={"detail": str(e)},
                    success=False,
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
        trip.status = "cancelled"
        trip.save()

        try:
            ensure_cancellation_confirmation_pdf(trip)
        except Exception as e:
            logger.warning(
                "Failed to generate cancellation confirmation PDF for trip %s: %s",
                trip.id,
                e
            )

        try:
            stop_trip_tracking(trip.id, reason="cancelled")
        except Exception:
            pass

        try:
            passenger_user = trip.passenger.user if trip.passenger else None
            if trip.is_paid and trip.stripe_payment_intent:
                refund_note = (
                    "Your payment has been refunded to your original payment method."
                )
            else:
                refund_note = "No card payment was refunded for this booking."
            if passenger_user:
                send_passenger_trip_cancellation_to_passenger(
                    passenger_user, trip, refund_note
                )
            send_passenger_trip_cancellation_to_admin(trip, refund_note)
        except Exception as e:
            logger.warning(
                "Failed to send passenger cancel emails for trip %s: %s", trip.id, e
            )

        return self.format_response(
            message=_("Trip cancelled successfully."),
            data={"trip_id": trip.id, "status": trip.status},
            status_code=status.HTTP_200_OK
        )
        
