from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from ..models import Trip
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from rest_framework.exceptions import ValidationError
from utils.common import get_locale, notify_user
from utils.common.email import send_trip_accepted_to_passenger, send_trip_accepted_to_admin
from utils.common.notifications import NOTIFICATION_TYPE_TRIP_ACCEPTED
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from apps.drivers.models import BaseDriver
from ..utils.time_conflict import driver_has_time_conflict
from apps.trips.services.booking_confirmation import ensure_booking_confirmation_pdf
import logging
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)



class AcceptTripAPIView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['post']

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        if not trip_id:
            raise ValidationError(_("Trip ID is required"))
        base_driver = get_object_or_404(BaseDriver, user_id=request.user.id)
        with transaction.atomic():
            try:
                trip = Trip.objects.select_for_update().get(id=trip_id, is_paid=True)
            except Trip.DoesNotExist:
                raise ValidationError(_("Trip not found"))
            if trip.status != "pending":
                raise ValidationError(_("Trip is not pending"))
            if trip.cancelled_by_driver and trip.cancelled_by_driver_id == base_driver:
                raise ValidationError(_("You cannot accept a trip that you have previously cancelled"))
            
            vehicle = base_driver.normal_driver.vehicle

            new_trip_datetime = timezone.make_aware(
                datetime.combine(trip.trip_date, trip.trip_time)
            )
            if driver_has_time_conflict(base_driver, new_trip_datetime, exclude_trip_id=trip.id):
                raise ValidationError(_("You cannot accept a trip that conflicts with an already scheduled trip"))

            if trip.car_type_id != vehicle.vehicle_type_id:
                raise ValidationError(_("You cannot accept a trip that does not match your vehicle type"))
            trip.base_driver = base_driver
            trip.status = "accepted"
            trip.cancelled_by_driver = False
            trip.cancelled_by_driver_id = None
            trip.cancellation_reason = None
            trip.cancelled_at = None
            trip.save(update_fields=[
                'base_driver', 
                'status',
                'cancelled_by_driver',
                'cancelled_by_driver_id',
                'cancellation_reason',
                'cancelled_at'
            ])

        passenger_user_id = trip.passenger.user_id if trip.passenger else None
        if passenger_user_id:
            notify_user(
                user=passenger_user_id,
                title_en='Trip Accepted',
                title_ar='تم قبول رحلتك',
                desc_en=f'Your trip #{trip.id} has been accepted by a driver.', 
                desc_ar=f'تم قبول رحلتك #{trip.id} من قبل سائق.',
                locale=locale,
                notification_type=NOTIFICATION_TYPE_TRIP_ACCEPTED, 
                trip_id=trip.id
            )
            try:
                pu = trip.passenger.user if trip.passenger else None
                if pu:
                    send_trip_accepted_to_passenger(pu, trip, request.user)
            except Exception as e:
                logger.warning("Failed to send trip-accepted email to passenger for trip %s: %s", trip.id, e)
        try:
            try:
                ensure_booking_confirmation_pdf(trip)
            except Exception as e:
                logger.warning("Failed to generate booking confirmation PDF for trip %s: %s", trip.id, e)

            send_trip_accepted_to_admin(trip, request.user)
        except Exception as e:
            logger.warning("Failed to send trip-accepted email to admin for trip %s: %s", trip.id, e)

        return Response({
            "success": True,
            "message": _("Trip accepted successfully"),
            "data": {
                "trip_id": trip.id,
                "status": trip.status
            }
        }, status=status.HTTP_200_OK)






