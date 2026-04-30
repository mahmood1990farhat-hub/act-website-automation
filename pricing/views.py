from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError, MethodNotAllowed
from django.db.models import Q
from decimal import Decimal

from .models import PricingSettings, PricingTier, PeakTimeRule, AirportFee
from .serializers import (
    PricingSettingsSerializer,
    PricingTierSerializer,
    PeakTimeRuleSerializer,
    AirportFeeSerializer
)
from utils.common.pagination import paginate_queryset
from utils.common.locale_utils import get_locale
from utils.common.error_handlers import (
    create_error_response,
    create_validation_error_response,
    get_bilingual_error_message
)
from django.utils.translation import activate
import logging

logger = logging.getLogger(__name__)


class PricingSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing PricingSettings (singleton).
    Only GET, PUT, and PATCH are allowed. Create and Delete are disabled.
    """
    serializer_class = PricingSettingsSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'put', 'patch']
    
    def get_queryset(self):
        """Return singleton instance"""
        settings, _ = PricingSettings.get_settings()
        return PricingSettings.objects.filter(pk=settings.pk)
    
    def list(self, request, *args, **kwargs):
        """Return the singleton settings object"""
        locale = get_locale(request)
        activate(locale)
        
        settings = PricingSettings.get_settings()
        serializer = self.get_serializer(settings)
        
        message = get_bilingual_error_message(
            'Pricing settings retrieved successfully.',
            'تم استرجاع إعدادات التسعير بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)
    
    def retrieve(self, request, *args, **kwargs):
        """Return the singleton settings object"""
        return self.list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Prevent creating new instances"""
        locale = get_locale(request)
        activate(locale)
        
        message = get_bilingual_error_message(
            'Cannot create new pricing settings. Use PUT or PATCH to update existing settings.',
            'لا يمكن إنشاء إعدادات تسعير جديدة. استخدم PUT أو PATCH لتحديث الإعدادات الموجودة.',
            locale
        )
        
        return create_error_response(
            message=message,
            errors=None,
            locale=locale,
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail='PricingSettings is a singleton. Use PUT or PATCH to update.'
        )
    
    def update(self, request, *args, **kwargs):
        """Update the singleton settings - works with or without ID in URL"""
        # For singleton, we can accept PUT on /settings/ or /settings/1/
        locale = get_locale(request)
        activate(locale)
        
        settings = PricingSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=False)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Pricing settings updated successfully.',
                'تم تحديث إعدادات التسعير بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_200_OK)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update the singleton settings - works with or without ID in URL"""
        locale = get_locale(request)
        activate(locale)
        
        settings = PricingSettings.get_settings()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Pricing settings updated successfully.',
                'تم تحديث إعدادات التسعير بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_200_OK)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def get_object(self):
        """Always return the singleton instance, regardless of URL parameter"""
        return PricingSettings.get_settings()
    
    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of singleton"""
        locale = get_locale(request)
        activate(locale)
        
        message = get_bilingual_error_message(
            'Cannot delete pricing settings. This is a required system configuration.',
            'لا يمكن حذف إعدادات التسعير. هذا إعداد مطلوب للنظام.',
            locale
        )
        
        return create_error_response(
            message=message,
            errors=None,
            locale=locale,
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail='PricingSettings cannot be deleted.'
        )


class PricingTierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing PricingTier.
    Supports filtering by vehicle_type_id, is_active, min_distance, max_distance.
    """
    serializer_class = PricingTierSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Get queryset with filtering"""
        queryset = PricingTier.objects.select_related('vehicle_type').all()
        
        # Filtering
        vehicle_type_id = self.request.query_params.get('vehicle_type_id')
        is_active = self.request.query_params.get('is_active')
        min_distance = self.request.query_params.get('min_distance')
        max_distance = self.request.query_params.get('max_distance')
        
        if vehicle_type_id:
            queryset = queryset.filter(vehicle_type_id=vehicle_type_id)
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)
        
        if min_distance:
            try:
                min_dist = Decimal(str(min_distance))
                queryset = queryset.filter(min_distance_miles__gte=min_dist)
            except (ValueError, TypeError):
                pass
        
        if max_distance:
            try:
                max_dist = Decimal(str(max_distance))
                queryset = queryset.filter(max_distance_miles__lte=max_dist)
            except (ValueError, TypeError):
                pass
        
        return queryset.order_by('vehicle_type', 'min_distance_miles')
    
    def list(self, request, *args, **kwargs):
        """List pricing tiers with pagination"""
        locale = get_locale(request)
        activate(locale)
        
        queryset = self.get_queryset()
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = self.get_serializer(page_obj, many=True)
        
        message = get_bilingual_error_message(
            'Pricing tiers retrieved successfully.',
            'تم استرجاع مستويات التسعير بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number if hasattr(page_obj, 'number') else 1,
                'page_size': paginator.per_page,
            }
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create a new pricing tier"""
        locale = get_locale(request)
        activate(locale)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Pricing tier created successfully.',
                'تم إنشاء مستوى التسعير بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_201_CREATED)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a pricing tier"""
        locale = get_locale(request)
        activate(locale)
        
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        message = get_bilingual_error_message(
            'Pricing tier retrieved successfully.',
            'تم استرجاع مستوى التسعير بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update a pricing tier"""
        locale = get_locale(request)
        activate(locale)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Pricing tier updated successfully.',
                'تم تحديث مستوى التسعير بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_200_OK)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a pricing tier"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a pricing tier"""
        locale = get_locale(request)
        activate(locale)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        
        message = get_bilingual_error_message(
            'Pricing tier deleted successfully.',
            'تم حذف مستوى التسعير بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': None,
            'pagination': None
        }, status=status.HTTP_200_OK)


class PeakTimeRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing PeakTimeRule.
    Supports filtering by vehicle_type_id, is_active, priority.
    """
    serializer_class = PeakTimeRuleSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Get queryset with filtering"""
        queryset = PeakTimeRule.objects.select_related('vehicle_type').all()
        
        # Filtering
        vehicle_type_id = self.request.query_params.get('vehicle_type_id')
        is_active = self.request.query_params.get('is_active')
        priority = self.request.query_params.get('priority')
        
        if vehicle_type_id:
            queryset = queryset.filter(vehicle_type_id=vehicle_type_id)
        elif vehicle_type_id == '':
            # Filter for global rules (vehicle_type is null)
            queryset = queryset.filter(vehicle_type__isnull=True)
        
        if is_active is not None:
            is_active_bool = is_active.lower() in ('true', '1', 'yes')
            queryset = queryset.filter(is_active=is_active_bool)
        
        if priority:
            try:
                priority_int = int(priority)
                queryset = queryset.filter(priority=priority_int)
            except (ValueError, TypeError):
                pass
        
        return queryset.order_by('-priority', 'start_time')
    
    def list(self, request, *args, **kwargs):
        """List peak time rules with pagination"""
        locale = get_locale(request)
        activate(locale)
        
        queryset = self.get_queryset()
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = self.get_serializer(page_obj, many=True)
        
        message = get_bilingual_error_message(
            'Peak time rules retrieved successfully.',
            'تم استرجاع قواعد أوقات الذروة بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number if hasattr(page_obj, 'number') else 1,
                'page_size': paginator.per_page,
            }
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create a new peak time rule"""
        locale = get_locale(request)
        activate(locale)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            created = getattr(serializer, '_created_instances', None)
            if created is not None and len(created) > 1:
                data = self.get_serializer(created, many=True).data
            else:
                data = serializer.data

            message = get_bilingual_error_message(
                'Peak time rule created successfully.',
                'تم إنشاء قاعدة وقت الذروة بنجاح.',
                locale
            )

            return Response({
                'success': True,
                'message': message,
                'data': data,
                'pagination': None
            }, status=status.HTTP_201_CREATED)
        else:
            return create_validation_error_response(serializer.errors, locale)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a peak time rule"""
        locale = get_locale(request)
        activate(locale)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        message = get_bilingual_error_message(
            'Peak time rule retrieved successfully.',
            'تم استرجاع قاعدة وقت الذروة بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update a peak time rule"""
        locale = get_locale(request)
        activate(locale)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Peak time rule updated successfully.',
                'تم تحديث قاعدة وقت الذروة بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_200_OK)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a peak time rule"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a peak time rule"""
        locale = get_locale(request)
        activate(locale)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        
        message = get_bilingual_error_message(
            'Peak time rule deleted successfully.',
            'تم حذف قاعدة وقت الذروة بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': None,
            'pagination': None
        }, status=status.HTTP_200_OK)


class AirportFeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AirportFee.
    Supports filtering by airport_id, vehicle_type_id.
    """
    serializer_class = AirportFeeSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Get queryset with filtering"""
        queryset = AirportFee.objects.select_related('airport', 'vehicle_type').all()
        
        # Filtering
        airport_id = self.request.query_params.get('airport_id')
        vehicle_type_id = self.request.query_params.get('vehicle_type_id')
        
        if airport_id:
            queryset = queryset.filter(airport_id=airport_id)
        
        if vehicle_type_id:
            queryset = queryset.filter(vehicle_type_id=vehicle_type_id)
        
        return queryset.order_by('airport', 'vehicle_type')
    
    def list(self, request, *args, **kwargs):
        """List airport fees with pagination"""
        locale = get_locale(request)
        activate(locale)
        
        queryset = self.get_queryset()
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = self.get_serializer(page_obj, many=True)
        
        message = get_bilingual_error_message(
            'Airport fees retrieved successfully.',
            'تم استرجاع رسوم المطار بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number if hasattr(page_obj, 'number') else 1,
                'page_size': paginator.per_page,
            }
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        """Create a new airport fee"""
        locale = get_locale(request)
        activate(locale)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Airport fee created successfully.',
                'تم إنشاء رسوم المطار بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_201_CREATED)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve an airport fee"""
        locale = get_locale(request)
        activate(locale)
        
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        message = get_bilingual_error_message(
            'Airport fee retrieved successfully.',
            'تم استرجاع رسوم المطار بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        """Update an airport fee"""
        locale = get_locale(request)
        activate(locale)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            
            message = get_bilingual_error_message(
                'Airport fee updated successfully.',
                'تم تحديث رسوم المطار بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data,
                'pagination': None
            }, status=status.HTTP_200_OK)
        else:
            return create_validation_error_response(serializer.errors, locale)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update an airport fee"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete an airport fee"""
        locale = get_locale(request)
        activate(locale)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        
        message = get_bilingual_error_message(
            'Airport fee deleted successfully.',
            'تم حذف رسوم المطار بنجاح.',
            locale
        )
        
        return Response({
            'success': True,
            'message': message,
            'data': None,
            'pagination': None
        }, status=status.HTTP_200_OK)

