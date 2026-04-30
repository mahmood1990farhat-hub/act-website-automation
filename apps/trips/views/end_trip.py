from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from apps.trips.models import Trip
from django.utils.translation import gettext as _, activate
from utils.common import get_locale, notify_user
from utils.common.notifications import NOTIFICATION_TYPE_TRIP_COMPLETED
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from apps.trips.services.trip_tracking import stop_trip_tracking
import logging

logger = logging.getLogger(__name__)


class CompleteTripView(EMADBaseView):
    http_method_names = ['post']
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            base_driver = user.base_driver
            if not base_driver:
                message = get_bilingual_error_message(
                    'Driver profile not found',
                    'ملف السائق غير موجود',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

            trip = Trip.objects.select_related(
                'passenger__user',
                'base_driver'
            ).get(id=trip_id, base_driver=base_driver)
        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found',
                'الرحلة غير موجودة',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)

        # Payment validation: trip must be paid before completion
        if not trip.is_paid:
            message = get_bilingual_error_message(
                'Trip payment not confirmed. Cannot complete trip.',
                'لم يتم تأكيد دفع الرحلة. لا يمكن إكمال الرحلة.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        status_choices = dict(Trip.STATUS_CHOICES)
        current_status_display = status_choices.get(trip.status, trip.status)
        
        if trip.status != "active":
            # If already completed, return success
            if trip.status == "completed":
                message = get_bilingual_error_message(
                    'Trip is already completed.',
                    'الرحلة مكتملة بالفعل.',
                    locale
                )
                return Response({
                    "success": True,
                    "message": message,
                    "data": {
                        "trip_id": trip.id,
                        "status": trip.status
                    }
                }, status=status.HTTP_200_OK)
            
            message = get_bilingual_error_message(
                f'Only active trips can be marked as completed. Current status: {current_status_display}',
                f'يمكن فقط إكمال الرحلات النشطة. الحالة الحالية: {current_status_display}',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            trip.status = "completed"
            trip.save(update_fields=['status'])

            # Note: Driver availability is managed through trip status checks
            # No need to set is_active on BaseDriver (it doesn't have that field)
            # The user.is_active field is for account activation, not trip availability

            logger.info(f"Trip {trip.id} completed by driver {user.id}")
            
            # Calculate earnings if trip is paid (system driver or guest driver)
            if trip.is_paid:
                try:
                    from apps.earnings.services.earnings_calculator import EarningsCalculator
                    earnings, revenue = EarningsCalculator.calculate_and_record_earnings(trip)
                    if earnings:
                        logger.info(f"Earnings calculated for trip {trip.id}: driver={earnings.net_amount}, company={revenue.amount}")
                    else:
                        logger.info(f"Earnings calculated for trip {trip.id}: company={revenue.amount} (guest driver)")
                except Exception as e:
                    logger.error(f"Error calculating earnings for trip {trip.id}: {str(e)}", exc_info=True)
                    # Don't fail trip completion, but log error

            # Notify passenger
            try:
                notify_user(
                    user=trip.passenger.user_id,
                    title_en='Trip Completed',
                    title_ar='اكتملت الرحلة',
                    desc_en=f'Your trip #{trip.id} has been completed. Thank you for using our service!',
                    desc_ar=f'اكتملت رحلتك #{trip.id}. شكراً لاستخدام خدمتنا!',
                    locale=locale,
                    notification_type=NOTIFICATION_TYPE_TRIP_COMPLETED,
                    trip_id=trip.id
                )
            except Exception as e:
                logger.warning(f"Failed to send notification for trip {trip.id}: {str(e)}")

            # إيقاف تتبع الرحلة (WebSocket + Redis)
            try:
                stop_trip_tracking(trip.id, reason="completed")
            except Exception as e:
                logger.warning(f"Failed to stop trip tracking for trip {trip.id}: {str(e)}")

            message = get_bilingual_error_message(
                'Trip completed successfully.',
                'تم إكمال الرحلة بنجاح.',
                locale
            )
            return Response({
                "success": True,
                "message": message,
                "data": {
                    "trip_id": trip.id,
                    "status": trip.status
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error completing trip {trip.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again.',
                'حدث خطأ. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)





