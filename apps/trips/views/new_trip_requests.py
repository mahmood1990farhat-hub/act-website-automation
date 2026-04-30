from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from rest_framework import status
from rest_framework.response import Response
from utils.common import paginate_queryset, get_locale
from utils.common.error_handlers import (
    create_error_response,
    get_bilingual_error_message
)
from django.utils.translation import gettext as _, activate
from ..serializers import TripWithStopPointBasicSerializer
from ..models import Trip
from apps.drivers.models import BaseDriver
import logging

logger = logging.getLogger(__name__)


def _ensure_driver_vehicle_type(base_driver):
    """
    If driver has a vehicle but vehicle_type is missing, try to set it from
    the driver's onboarding request (step 1 choice). Returns True if vehicle_type
    is now set (or was already set), False otherwise.
    """
    try:
        normal_driver = base_driver.normal_driver
        vehicle = normal_driver.vehicle
    except AttributeError:
        return False
    if vehicle.vehicle_type_id:
        return True
    try:
        onboarding_request = base_driver.user.driver_onboarding_request
    except Exception:
        return False
    if not getattr(onboarding_request, 'vehicle_type', None):
        return False
    from apps.vehicle.utils import get_vehicle_type_from_string
    vt = get_vehicle_type_from_string(onboarding_request.vehicle_type)
    if not vt:
        return False
    vehicle.vehicle_type = vt
    vehicle.save(update_fields=['vehicle_type'])
    logger.info(
        "Set vehicle_type for driver %s from onboarding_request: %s",
        base_driver.id,
        onboarding_request.vehicle_type,
    )
    return True


class NewTripRequestsView(EMADBaseView):
    http_method_names = ['get']
    permission_classes = [IsNormalDriver, IsVerifiedAndProfileCompleted]

    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            base_driver = BaseDriver.objects.select_related(
                'normal_driver__vehicle__vehicle_type'
            ).get(user=user)
        except BaseDriver.DoesNotExist:
            message = get_bilingual_error_message(
                'User is not a driver.',
                'المستخدم ليس سائقاً.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            driver_vehicle_type = base_driver.normal_driver.vehicle.vehicle_type
            driver_max_passengers = driver_vehicle_type.max_passengers_count
        except AttributeError:
            # Try to recover: set vehicle_type from onboarding request (step 1 choice) if possible
            driver_vehicle_type = None
            driver_max_passengers = None
            if _ensure_driver_vehicle_type(base_driver):
                base_driver.refresh_from_db()
                try:
                    driver_vehicle_type = base_driver.normal_driver.vehicle.vehicle_type
                    driver_max_passengers = driver_vehicle_type.max_passengers_count
                except AttributeError:
                    pass
            if not driver_vehicle_type or not driver_max_passengers:
                message = get_bilingual_error_message(
                    'Driver vehicle or vehicle type is not set. Please complete your profile or contact support.',
                    'لم يتم تعيين مركبة السائق أو نوع المركبة. يرجى إكمال الملف الشخصي أو الاتصال بالدعم.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        # Filter trips: pending status, passenger count <= driver's vehicle capacity
        # Vehicle capacity determines which rides you can see:
        # - 5-seat cars: Rides with 1-5 passengers
        # - 7-seat cars: Rides with 1-7 passengers
        # This pattern continues for larger vehicles
        # Note: Cancelled trips (status='pending', cancelled_by_driver=True) are available for other drivers
        # but excluded for the cancelling driver
        queryset = Trip.objects.filter(
            status='pending',
            passengers_count__lte=driver_max_passengers,  # Passenger count <= driver's vehicle capacity
            base_driver__isnull=True  # Only show unassigned trips
        ).exclude(
            # Exclude trips cancelled by this driver (they can't accept their own cancelled trips)
            cancelled_by_driver_id=base_driver
        ).select_related(
            'airport',
            'passenger__user',
            'car_type',
            'cancelled_by_driver_id__user'
        ).prefetch_related('stop_points').order_by('-created_at')

        page_obj, paginator = paginate_queryset(queryset, request)

        serializer = TripWithStopPointBasicSerializer(
            page_obj,
            many=True,
            context={
                "request": request,
                "account_type": user.account_type,
                "for_driver": True,
                "base_driver": base_driver,
            },
        )

        return Response({
            "trips": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)





