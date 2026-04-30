from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from ..models import Trip
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from utils.common import get_locale, notify_user
from utils.common.notifications import NOTIFICATION_TYPE_DRIVER_CANCELLED
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from utils.common.email import (
    send_driver_cancellation_to_passenger,
    send_driver_cancellation_to_admin
)
from apps.trips.services.trip_tracking import stop_trip_tracking
import logging

logger = logging.getLogger(__name__)


class DriverCancelTripView(EMADBaseView):
    """
    Driver cancels a trip after accepting it
    POST /api/trips/<trip_id>/driver-cancel/
    
    Request body (optional):
    {
        "cancellation_reason": "Emergency situation"
    }
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['post']

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            # Get driver's base_driver profile
            base_driver = user.base_driver
            if not base_driver:
                message = get_bilingual_error_message(
                    'Driver profile not found',
                    'ملف السائق غير موجود',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

            # Use database transaction with select_for_update to prevent race conditions
            with transaction.atomic():
                # Lock the trip row for update to prevent concurrent modifications
                # Note: select_for_update() cannot be used with select_related() on nullable foreign keys
                # We'll fetch the trip with the lock first, then access related objects normally (lazy loading)
                trip = Trip.objects.select_for_update().get(id=trip_id, base_driver=base_driver)
                # Related objects (passenger, base_driver) will be fetched lazily when accessed
                # This is safe within the transaction and avoids the outer join issue
                
                # Validate trip ownership - must belong to this driver (already checked in get())
                
                # Validate trip status - can only cancel if accepted, driver_on_the_way, or active
                allowed_statuses = ['accepted', 'driver_on_the_way', 'active']
                if trip.status not in allowed_statuses:
                    status_choices = dict(Trip.STATUS_CHOICES)
                    current_status_display = status_choices.get(trip.status, trip.status)
                    message = get_bilingual_error_message(
                        f'You can only cancel trips that are accepted, on the way, or active. Current status: {current_status_display}',
                        f'يمكنك إلغاء الرحلات المقبولة أو في الطريق أو النشطة فقط. الحالة الحالية: {current_status_display}',
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

                # Check if trip is already cancelled
                if trip.cancelled_by_driver:
                    message = get_bilingual_error_message(
                        'This trip has already been cancelled',
                        'تم إلغاء هذه الرحلة بالفعل',
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

                # Get cancellation reason from request if provided
                cancellation_reason = request.data.get('cancellation_reason', '').strip()

                # Use the reusable cancellation method
                trip.cancel_by_driver(base_driver, cancellation_reason)
                
                # Save the trip with all updated fields
                trip.save(update_fields=[
                    'cancelled_by_driver',
                    'cancelled_by_driver_id',
                    'cancelled_at',
                    'cancellation_reason',
                    'base_driver',
                    'status',
                    'is_guest_driver',
                    'guest_driver_name',
                    'guest_driver_phone',
                    'guest_driver_company'
                ])
                
                # Refresh from database to verify save
                trip.refresh_from_db()
                logger.info(
                    f"Trip {trip.id} cancelled by driver {base_driver.id} (user {user.id}). "
                    f"Status: {trip.status}, cancelled_by_driver: {trip.cancelled_by_driver}, "
                    f"cancelled_by_driver_id: {trip.cancelled_by_driver_id_id if trip.cancelled_by_driver_id else None}, "
                    f"base_driver: {trip.base_driver_id}"
                )
                
                # Fetch related objects for notifications (outside the locked query)
                # Accessing related objects lazily is safe here
                passenger_user = trip.passenger.user if trip.passenger else None

                try:
                    stop_trip_tracking(trip.id, reason="driver_cancelled")
                except Exception as e:
                    logger.warning(f"Failed to stop trip tracking for trip {trip.id}: {str(e)}")

        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found or you are not assigned to this trip',
                'الرحلة غير موجودة أو أنك غير معين لهذه الرحلة',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)

        try:
            # Send notifications and emails outside transaction to avoid long locks
            if passenger_user:
                try:
                    notify_user(
                        user=passenger_user.id,
                        title_en='Driver Cancelled Trip',
                        title_ar='ألغى السائق الرحلة',
                        desc_en=f'Driver has cancelled trip #{trip.id}. We will connect you with another driver shortly.',
                        desc_ar=f'ألغى السائق رحلتك #{trip.id}. سنقوم بالاتصال بك مع سائق آخر قريباً.',
                        locale=locale,
                        notification_type=NOTIFICATION_TYPE_DRIVER_CANCELLED,
                        trip_id=trip.id
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for trip {trip.id}: {str(e)}")

                # Send email to passenger
                try:
                    send_driver_cancellation_to_passenger(passenger_user, trip)
                except Exception as e:
                    logger.warning(f"Failed to send email to passenger for trip {trip.id}: {str(e)}")

            # Send email to admin
            try:
                send_driver_cancellation_to_admin(trip)
            except Exception as e:
                logger.warning(f"Failed to send email to admin for trip {trip.id}: {str(e)}")

            message = get_bilingual_error_message(
                'Trip cancelled successfully. The passenger and admin have been notified.',
                'تم إلغاء الرحلة بنجاح. تم إشعار الراكب والمسؤول.',
                locale
            )
            return Response({
                "success": True,
                "message": message,
                "data": {
                    "trip_id": trip.id,
                    "status": trip.status,
                    "cancelled_at": trip.cancelled_at.isoformat() if trip.cancelled_at else None
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error cancelling trip {trip.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred while cancelling the trip. Please try again.',
                'حدث خطأ أثناء إلغاء الرحلة. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

