from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from ..serializers import CustomUserSerializer, NormalDriverSerializer
from ..serializers.detail_serializers import DriverDetailSerializer
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from utils.common import paginate_queryset, get_locale
from utils.common.error_handlers import (
    create_not_found_response,
    get_bilingual_error_message
)
from rest_framework import status 
from django.db.models import Count, Prefetch, Q
from apps.drivers.models import NormalDriver
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.translation import activate
import logging

logger = logging.getLogger(__name__)
CustomUser = get_user_model()

class NormalDriverListView(EMADBaseView):
    """
    Admin Panel - List drivers with pagination and search
    GET /api/admin-panel/normal-drivers/
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10)
    - is_active: Filter by active status (true/false)
    - search: Search in name, email, phone number, vehicle number
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Build base queryset with optimizations
        queryset = NormalDriver.objects.select_related(
            'driver__user',          
            'driver__bank_details',  
            'vehicle',
            'vehicle__vehicle_type'
        ).prefetch_related(
            Prefetch('driver__trips')
        )

        # Filter by is_active
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(driver__user__is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(driver__user__is_active=False)

        # Search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(driver__user__first_name__icontains=search) |
                Q(driver__user__last_name__icontains=search) |
                Q(driver__user__email__icontains=search) |
                Q(driver__user__phone_number__icontains=search) |
                Q(driver__user__address__icontains=search) |
                Q(vehicle__vehicle_number__icontains=search)
            )

        # Order by most recent first
        queryset = queryset.order_by('-driver__user__date_joined')

        # Get statistics for all drivers (before filtering)
        all_drivers_stats = NormalDriver.objects.select_related('driver__user').aggregate(
            total=Count('id'),
            active_count=Count('id', filter=Q(driver__user__is_active=True)),
            inactive_count=Count('id', filter=Q(driver__user__is_active=False)),
            verified_count=Count('id', filter=Q(driver__user__is_admin_verified=True)),
            unverified_count=Count('id', filter=Q(driver__user__is_admin_verified=False)),
            profile_completed_count=Count('id', filter=Q(driver__user__is_profile_completed=True)),
            profile_incomplete_count=Count('id', filter=Q(driver__user__is_profile_completed=False)),
        )

        # Paginate
        page_obj, paginator = paginate_queryset(queryset=queryset, request=request)
        serializer = NormalDriverSerializer(page_obj, many=True, context={'request': request})

        # Get filtered statistics
        filtered_stats = queryset.aggregate(
            count=Count('id')
        )

        return Response({
            "success": True,
            "message": get_bilingual_error_message(
                "Drivers retrieved successfully.",
                "تم جلب السائقين بنجاح.",
                locale
            ),
            "data": {
                "drivers": serializer.data,
                "stats": {
                    "all_time": all_drivers_stats,
                    "filtered": {
                        "count": filtered_stats['count']
                    }
                },
                "filters_applied": {
                    "is_active": is_active,
                    "search": search
                }
            },
            "pagination": {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "current_page": page_obj.number if hasattr(page_obj, 'number') else 1,
                "page_size": paginator.per_page,
            }
        }, status=status.HTTP_200_OK)


class DriverDetailView(APIView):
    """
    Get full driver information by user ID or driver ID
    GET /api/admin-panel/normal-drivers/<id>/
    
    Note: The ID can be either:
    - User ID (as shown in the list API response: driver.user.id)
    - NormalDriver ID (as shown in the list API response: driver.id)
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request, driver_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            id_value = int(driver_id)
            
            # Try to find by user_id first (since list API shows user.id)
            driver = None
            try:
                driver = NormalDriver.objects.select_related(
                    'driver__user',
                    'driver__bank_details',
                    'vehicle',
                    'vehicle__vehicle_type'
                ).prefetch_related(
                    Prefetch('driver__trips'),
                    'driver__trips__passenger__user',
                    'driver__trips__car_type',
                    'driver__trips__stop_points',
                    'driver__user__driver_onboarding_request'
                ).get(driver__user_id=id_value)
            except NormalDriver.DoesNotExist:
                # If not found by user_id, try by NormalDriver id
                try:
                    driver = NormalDriver.objects.select_related(
                        'driver__user',
                        'driver__bank_details',
                        'vehicle',
                        'vehicle__vehicle_type'
                    ).prefetch_related(
                        Prefetch('driver__trips'),
                        'driver__trips__passenger__user',
                        'driver__trips__car_type',
                        'driver__trips__stop_points',
                        'driver__user__driver_onboarding_request'
                    ).get(id=id_value)
                except NormalDriver.DoesNotExist:
                    message = get_bilingual_error_message(
                        'Driver not found.',
                        'السائق غير موجود.',
                        locale
                    )
                    return create_not_found_response(message, locale)
                    
        except (ValueError, TypeError):
            message = get_bilingual_error_message(
                'Invalid driver ID.',
                'معرف السائق غير صالح.',
                locale
            )
            return create_not_found_response(message, locale)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching driver detail: {str(e)}")
            message = get_bilingual_error_message(
                'Driver not found.',
                'السائق غير موجود.',
                locale
            )
            return create_not_found_response(message, locale)
        
        serializer = DriverDetailSerializer(driver, context={'request': request})
        
        message = get_bilingual_error_message(
            'Driver details retrieved successfully.',
            'تم جلب تفاصيل السائق بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)
