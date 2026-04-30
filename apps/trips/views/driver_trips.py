from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsNormalDriver, IsVerifiedAndProfileCompleted
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from django.shortcuts import get_object_or_404
from utils.common import get_locale, paginate_queryset
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    get_bilingual_error_message
)
from ..models import Trip
from ..serializers import TripWithStopPointSerializer
from apps.drivers.models import BaseDriver
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class DriverTripsListView(EMADBaseView):
    """
    List all trips assigned to the authenticated driver with pagination and filtering
    GET /api/driver/trips/
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['get']

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
                'Driver profile not found.',
                'ملف السائق غير موجود.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        # Get status filter from query params
        trip_status_param = request.query_params.get('status', '').strip()
        
        # Build queryset - include trips assigned to this driver
        # Exclude pending trips that were cancelled by this driver (they're available for other drivers)
        queryset = Trip.objects.filter(
            base_driver=base_driver  # Only trips currently assigned to this driver
        ).exclude(
            # Exclude pending trips cancelled by this driver
            # These are available for other drivers, not the cancelling driver
            Q(status='pending', cancelled_by_driver=True, cancelled_by_driver_id=base_driver)
        ).select_related(
            'passenger__user',
            'car_type',
            'airport',
            'base_driver__user',
            'base_driver__normal_driver__vehicle',
            'cancelled_by_driver_id__user'
        ).prefetch_related('stop_points').order_by('-created_at')

        # Apply status filter if provided
        if trip_status_param:
            trip_statuses = [s.strip() for s in trip_status_param.split(',')]
            allowed_statuses = ['pending', 'accepted', 'driver_on_the_way', 'active', 'completed', 'cancelled']
            
            invalid_statuses = [s for s in trip_statuses if s not in allowed_statuses]
            if invalid_statuses:
                message = get_bilingual_error_message(
                    f'Invalid trip status: {", ".join(invalid_statuses)}',
                    f'حالة الرحلة غير صالحة: {", ".join(invalid_statuses)}',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            queryset = queryset.filter(status__in=trip_statuses)

        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        
        # Serialize
        serializer = TripWithStopPointSerializer(
            page_obj,
            many=True,
            context={'request': request, 'account_type': 'normal_driver'}
        )

        message = get_bilingual_error_message(
            'Trips retrieved successfully.',
            'تم جلب الرحلات بنجاح.',
            locale
        )

        return Response({
            'success': True,
            'message': message,
            'data': {
                'trips': serializer.data
            },
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'page_size': paginator.per_page
            }
        }, status=status.HTTP_200_OK)


class DriverTripDetailView(EMADBaseView):
    """
    Get trip details by ID for the authenticated driver
    GET /api/driver/trips/{id}/
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['get']

    def handle_get(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            base_driver = BaseDriver.objects.get(user=user)
        except BaseDriver.DoesNotExist:
            message = get_bilingual_error_message(
                'Driver profile not found.',
                'ملف السائق غير موجود.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            # Get trip that belongs to this driver (currently assigned)
            # Exclude pending trips cancelled by this driver
            trip = Trip.objects.filter(
                base_driver=base_driver
            ).exclude(
                Q(status='pending', cancelled_by_driver=True, cancelled_by_driver_id=base_driver)
            ).select_related(
                'passenger__user',
                'car_type',
                'airport',
                'base_driver__user',
                'base_driver__normal_driver__vehicle',
                'cancelled_by_driver_id__user'
            ).prefetch_related('stop_points').get(id=trip_id)
            
            # Additional validation: Verify trip ownership
            if trip.base_driver != base_driver:
                message = get_bilingual_error_message(
                    'Trip not found or you do not have permission to view it.',
                    'الرحلة غير موجودة أو ليس لديك إذن لعرضها.',
                    locale
                )
                return create_not_found_response(message, locale)
            
            # Verify trip is not a pending trip cancelled by this driver
            if trip.status == 'pending' and trip.cancelled_by_driver and trip.cancelled_by_driver_id == base_driver:
                message = get_bilingual_error_message(
                    'Trip not found or you do not have permission to view it.',
                    'الرحلة غير موجودة أو ليس لديك إذن لعرضها.',
                    locale
                )
                return create_not_found_response(message, locale)
                
        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found or you do not have permission to view it.',
                'الرحلة غير موجودة أو ليس لديك إذن لعرضها.',
                locale
            )
            return create_not_found_response(message, locale)

        serializer = TripWithStopPointSerializer(
            trip,
            context={'request': request, 'account_type': 'normal_driver'}
        )

        message = get_bilingual_error_message(
            'Trip details retrieved successfully.',
            'تم جلب تفاصيل الرحلة بنجاح.',
            locale
        )

        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)

