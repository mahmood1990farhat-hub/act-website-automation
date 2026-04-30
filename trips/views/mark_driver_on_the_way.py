from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from rest_framework.response import Response
from rest_framework import status
from ..models import Trip
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _, activate
from utils.common import get_locale, notify_user
from utils.common.notifications import NOTIFICATION_TYPE_DRIVER_ON_THE_WAY
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
import logging

logger = logging.getLogger(__name__)


class MarkDriverOnTheWayView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['post']

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

        status_choices = dict(Trip.STATUS_CHOICES)
        current_status_display = status_choices.get(trip.status, trip.status)
        
        if trip.status != 'accepted':
            # If already on the way, return success
            if trip.status == 'driver_on_the_way':
                message = get_bilingual_error_message(
                    'Driver is already marked as on the way.',
                    'تم وضع السائق في الطريق بالفعل.',
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
                f'Trip status must be "accepted" to mark driver as on the way. Current status: {current_status_display}',
                f'يجب أن تكون حالة الرحلة "مقبولة" لوضع السائق في الطريق. الحالة الحالية: {current_status_display}',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            trip.status = 'driver_on_the_way'
            trip.save(update_fields=['status'])

            logger.info(f"Driver {user.id} marked as on the way for trip {trip.id}")

            # Notify passenger
            try:
                notify_user(
                    user=trip.passenger.user_id,
                    title_en='Driver On The Way',
                    title_ar='السائق في الطريق',
                    desc_en=f'Your driver is on the way to pick you up for trip #{trip.id}.',
                    desc_ar=f'سائقك في الطريق لاصطحابك لرحلة #{trip.id}.',
                    locale=locale,
                    notification_type=NOTIFICATION_TYPE_DRIVER_ON_THE_WAY,
                    trip_id=trip.id
                )
            except Exception as e:
                logger.warning(f"Failed to send notification for trip {trip.id}: {str(e)}")

            message = get_bilingual_error_message(
                'Driver marked as on the way successfully',
                'تم وضع السائق في الطريق بنجاح',
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
            logger.error(f"Error marking driver on the way for trip {trip.id}: {str(e)}", exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again.',
                'حدث خطأ. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        


        





