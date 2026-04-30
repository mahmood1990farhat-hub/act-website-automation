from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAdminUser
from ..serializers import CustomUserSerializer
from ..serializers.detail_serializers import PassengerDetailSerializer
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from utils.common import paginate_queryset, get_locale
from utils.common.error_handlers import (
    create_not_found_response,
    get_bilingual_error_message
)
from rest_framework import status 
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from apps.passengers.models import Passenger
from django.utils.translation import activate
import logging

logger = logging.getLogger(__name__)
CustomUser = get_user_model()

class PassengerUserListView(EMADBaseView):
    """
    Admin Panel - List passengers with pagination and search
    GET /api/admin-panel/passengers/
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10)
    - is_active: Filter by active status (true/false)
    - search: Search in name, email, phone number
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Build base queryset
        passengers_qs = CustomUser.objects.prefetch_related(
            'passenger_profile', 
            'passenger_profile__trips'
        ).filter(account_type='passenger')

        # Filter by is_active
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                passengers_qs = passengers_qs.filter(is_active=True)
            elif is_active.lower() == 'false':
                passengers_qs = passengers_qs.filter(is_active=False)

        # Search functionality
        search = request.query_params.get('search')
        if search:
            passengers_qs = passengers_qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone_number__icontains=search) |
                Q(address__icontains=search)
            )

        # Order by most recent first
        passengers_qs = passengers_qs.order_by('-date_joined')

        # Get statistics for all passengers (before filtering)
        all_passengers_stats = CustomUser.objects.filter(account_type='passenger').aggregate(
            total=Count('id'),
            active_count=Count('id', filter=Q(is_active=True)),
            inactive_count=Count('id', filter=Q(is_active=False)),
            verified_count=Count('id', filter=Q(is_admin_verified=True)),
            unverified_count=Count('id', filter=Q(is_admin_verified=False)),
            profile_completed_count=Count('id', filter=Q(is_profile_completed=True)),
            profile_incomplete_count=Count('id', filter=Q(is_profile_completed=False)),
        )

        # Paginate
        page_obj, paginator = paginate_queryset(queryset=passengers_qs, request=request)
        serializer = CustomUserSerializer(page_obj, many=True, context={'request': request})

        # Get filtered statistics
        filtered_stats = passengers_qs.aggregate(
            count=Count('id')
        )

        return Response({
            "success": True,
            "message": get_bilingual_error_message(
                "Passengers retrieved successfully.",
                "تم جلب الركاب بنجاح.",
                locale
            ),
            "data": {
                "passengers": serializer.data,
                "stats": {
                    "all_time": all_passengers_stats,
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


class PassengerDetailView(APIView):
    """
    Get full passenger information by user ID
    GET /api/admin-panel/passengers/<user_id>/
    
    Note: The ID should be the user ID (as shown in the list API), not the Passenger model ID
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request, passenger_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            # Try to find by user_id first (since list API returns user IDs)
            # passenger_id is actually the user_id from the list response
            user_id = int(passenger_id)
            
            # First check if user exists and is a passenger
            user = get_object_or_404(
                CustomUser.objects.filter(account_type='passenger'),
                id=user_id
            )
            
            # Get the passenger profile
            try:
                passenger = Passenger.objects.select_related('user').prefetch_related(
                    'trips',
                    'trips__base_driver__user',
                    'trips__car_type',
                    'trips__stop_points'
                ).get(user_id=user_id)
            except Passenger.DoesNotExist:
                message = get_bilingual_error_message(
                    'Passenger profile not found for this user.',
                    'لم يتم العثور على ملف الراكب لهذا المستخدم.',
                    locale
                )
                return create_not_found_response(message, locale)
                
        except (ValueError, TypeError):
            message = get_bilingual_error_message(
                'Invalid passenger ID.',
                'معرف الراكب غير صالح.',
                locale
            )
            return create_not_found_response(message, locale)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching passenger detail: {str(e)}")
            message = get_bilingual_error_message(
                'Passenger not found.',
                'الراكب غير موجود.',
                locale
            )
            return create_not_found_response(message, locale)
        
        serializer = PassengerDetailSerializer(passenger, context={'request': request})
        
        message = get_bilingual_error_message(
            'Passenger details retrieved successfully.',
            'تم جلب تفاصيل الراكب بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)

