from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from apps.accounts.permissions import IsVerifiedAndProfileCompleted, IsNormalDriver
from django.utils.translation import gettext as _, activate
from utils.common import get_locale, notify_user
from utils.common.notifications import NOTIFICATION_TYPE_TRIP_STARTED
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from ..models import Trip
from rest_framework.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class StartTripView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            trip = Trip.objects.select_related(
                'passenger__user',
                'base_driver'
            ).get(id=trip_id, base_driver__user_id=user.id)
        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found',
                'الرحلة غير موجودة',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)

        # Payment validation: trip must be paid before starting
        if not trip.is_paid:
            message = get_bilingual_error_message(
                'Trip payment not confirmed. Cannot start trip.',
                'لم يتم تأكيد دفع الرحلة. لا يمكن بدء الرحلة.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        status_choices = dict(Trip.STATUS_CHOICES)
        current_status_display = status_choices.get(trip.status, trip.status)
        
        if trip.status != 'driver_on_the_way':
            # If already active, return success
            if trip.status == 'active':
                message = get_bilingual_error_message(
                    'Trip is already active.',
                    'الرحلة نشطة بالفعل.',
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
                f'Trip must be in "driver_on_the_way" status to start. Current status: {current_status_display}',
                f'يجب أن تكون حالة الرحلة "السائق في الطريق" لبدء الرحلة. الحالة الحالية: {current_status_display}',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            trip.status = 'active'
            trip.save(update_fields=['status'])

            logger.info(f"Trip {trip.id} started by driver {user.id}")

            # Notify passenger
            try:
                notify_user(
                    user=trip.passenger.user_id,
                    title_en='Trip Started',
                    title_ar='بدأت الرحلة',
                    desc_en=f'Your trip #{trip.id} has started.',
                    desc_ar=f'بدأت رحلتك #{trip.id}.',
                    locale=locale,
                    notification_type=NOTIFICATION_TYPE_TRIP_STARTED,
                    trip_id=trip.id
                )
            except Exception as e:
                logger.warning(f"Failed to send notification for trip {trip.id}: {str(e)}")

            message = get_bilingual_error_message(
                'Trip started and is now active.',
                'بدأت الرحلة وهي الآن نشطة.',
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
            logger.error(f"Error starting trip {trip.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again.',
                'حدث خطأ. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


