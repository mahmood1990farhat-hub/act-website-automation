from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
from apps.accounts.permissions import IsVerifiedAndProfileCompleted, IsNormalDriver
from apps.drivers.operational_safety import lock_driver_record
from django.db import transaction
from django.utils import timezone
from django.utils.translation import activate
from utils.common import get_locale, notify_user
from utils.common.notifications import NOTIFICATION_TYPE_TRIP_STARTED
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from ..models import Trip
import logging

logger = logging.getLogger(__name__)


class StartTripView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            # Match the common operational-safety lock order: driver, then
            # profile, then trip. Read status after the row lock so concurrent
            # starts preserve the first timestamp and emit one transition.
            with transaction.atomic():
                driver, _profile = lock_driver_record(user.base_driver.pk)
                trip = Trip.objects.select_for_update().get(
                    id=trip_id, base_driver=driver,
                )

                if not trip.is_paid:
                    message = get_bilingual_error_message(
                        'Trip payment not confirmed. Cannot start trip.',
                        'لم يتم تأكيد دفع الرحلة. لا يمكن بدء الرحلة.',
                        locale
                    )
                    return create_error_response(
                        message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST,
                    )

                if trip.status == 'active':
                    # Legacy active trips retain a missing timestamp. A retry
                    # cannot establish when their original start occurred.
                    message = get_bilingual_error_message(
                        'Trip is already active.',
                        'الرحلة نشطة بالفعل.',
                        locale
                    )
                    return Response({
                        "success": True,
                        "message": message,
                        "data": {"trip_id": trip.id, "status": trip.status},
                    }, status=status.HTTP_200_OK)

                if trip.status != 'driver_on_the_way':
                    current_status_display = dict(Trip.STATUS_CHOICES).get(
                        trip.status, trip.status,
                    )
                    message = get_bilingual_error_message(
                        f'Trip must be in "driver_on_the_way" status to start. Current status: {current_status_display}',
                        f'يجب أن تكون حالة الرحلة "السائق في الطريق" لبدء الرحلة. الحالة الحالية: {current_status_display}',
                        locale
                    )
                    return create_error_response(
                        message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST,
                    )

                trip.status = 'active'
                if trip.started_at is None:
                    trip.started_at = timezone.now()
                trip.save(update_fields=['status', 'started_at'])

        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found',
                'الرحلة غير موجودة',
                locale
            )
            return create_error_response(
                message, locale=locale, status_code=status.HTTP_404_NOT_FOUND,
            )
        except APIException:
            # Keep the existing operational-safety conflict response intact.
            raise
        except Exception as exc:
            logger.error("Error starting trip %s: %s", trip_id, exc, exc_info=True)
            message = get_bilingual_error_message(
                'An error occurred. Please try again.',
                'حدث خطأ. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(
                message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Trip %s started by driver %s", trip.id, user.id)

        # Existing passenger notification follows the successful transaction
        # and only the request that actually changed the status reaches it.
        try:
            if trip.passenger:
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
        except Exception as exc:
            logger.warning("Failed to send notification for trip %s: %s", trip.id, exc)

        message = get_bilingual_error_message(
            'Trip started and is now active.',
            'بدأت الرحلة وهي الآن نشطة.',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {"trip_id": trip.id, "status": trip.status},
        }, status=status.HTTP_200_OK)

