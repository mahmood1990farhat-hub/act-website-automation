"""
Admin panel views for updating user information (driver and passenger)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _, activate
from utils.common import get_locale
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    create_validation_error_response,
    get_bilingual_error_message
)
from ..serializers.user_update import (
    AdminUpdateDriverSerializer,
    AdminUpdatePassengerSerializer
)
from apps.drivers.models import NormalDriver
from apps.passengers.models import Passenger
import logging

logger = logging.getLogger(__name__)


class UpdateDriverInfoView(EMADBaseView):
    """
    Update driver information (user, vehicle, bank details, documents)
    PUT/PATCH /api/admin-panel/drivers/<driver_id>/update/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['put', 'patch']
    
    def handle_put(self, request, driver_id):
        return self._handle_update(request, driver_id, partial=False)
    
    def handle_patch(self, request, driver_id):
        return self._handle_update(request, driver_id, partial=True)
    
    def _handle_update(self, request, driver_id, partial=False):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            driver = get_object_or_404(
                NormalDriver.objects.select_related(
                    'driver__user',
                    'driver__bank_details',
                    'vehicle',
                    'vehicle__vehicle_type'
                ),
                id=driver_id
            )
        except Exception:
            message = get_bilingual_error_message(
                'Driver not found.',
                'السائق غير موجود.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # Prepare data for serializer
        data = {
            'user_data': request.data.get('user_data', {}),
            'vehicle_data': request.data.get('vehicle_data', {}),
            'bank_details_data': request.data.get('bank_details_data', {}),
        }
        
        # Handle file uploads
        if 'pco' in request.FILES:
            data['pco'] = request.FILES['pco']
        if 'dbs' in request.FILES:
            data['dbs'] = request.FILES['dbs']
        if 'dvla' in request.FILES:
            data['dvla'] = request.FILES['dvla']
        
        serializer = AdminUpdateDriverSerializer(driver, data=data, partial=partial)
        
        if serializer.is_valid():
            try:
                updated_driver = serializer.save()
                logger.info(f"Admin {request.user.id} updated driver {driver_id}")
                
                message = get_bilingual_error_message(
                    'Driver information updated successfully.',
                    'تم تحديث معلومات السائق بنجاح.',
                    locale
                )
                
                # Return updated driver data
                from ..serializers import NormalDriverSerializer
                driver_serializer = NormalDriverSerializer(updated_driver, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': message,
                    'data': driver_serializer.data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error updating driver {driver_id}: {str(e)}")
                message = get_bilingual_error_message(
                    'An error occurred while updating driver information.',
                    'حدث خطأ أثناء تحديث معلومات السائق.',
                    locale
                )
                return create_error_response(message, locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return create_validation_error_response(
                serializer.errors,
                locale,
                get_bilingual_error_message(
                    'Validation error.',
                    'خطأ في التحقق.',
                    locale
                )
            )


class UpdatePassengerInfoView(EMADBaseView):
    """
    Update passenger information
    PUT/PATCH /api/admin-panel/passengers/<passenger_id>/update/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['put', 'patch']
    
    def handle_put(self, request, passenger_id):
        return self._handle_update(request, passenger_id, partial=False)
    
    def handle_patch(self, request, passenger_id):
        return self._handle_update(request, passenger_id, partial=True)
    
    def _handle_update(self, request, passenger_id, partial=False):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            passenger = get_object_or_404(
                Passenger.objects.select_related('user'),
                id=passenger_id
            )
        except Exception:
            message = get_bilingual_error_message(
                'Passenger not found.',
                'الراكب غير موجود.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # Prepare data for serializer
        data = {
            'user_data': request.data.get('user_data', {}),
        }
        
        serializer = AdminUpdatePassengerSerializer(passenger, data=data, partial=partial)
        
        if serializer.is_valid():
            try:
                updated_passenger = serializer.save()
                logger.info(f"Admin {request.user.id} updated passenger {passenger_id}")
                
                message = get_bilingual_error_message(
                    'Passenger information updated successfully.',
                    'تم تحديث معلومات الراكب بنجاح.',
                    locale
                )
                
                # Return updated passenger data
                from ..serializers import CustomUserSerializer
                user_serializer = CustomUserSerializer(updated_passenger.user, context={'request': request})
                
                return Response({
                    'success': True,
                    'message': message,
                    'data': user_serializer.data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Error updating passenger {passenger_id}: {str(e)}")
                message = get_bilingual_error_message(
                    'An error occurred while updating passenger information.',
                    'حدث خطأ أثناء تحديث معلومات الراكب.',
                    locale
                )
                return create_error_response(message, locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return create_validation_error_response(
                serializer.errors,
                locale,
                get_bilingual_error_message(
                    'Validation error.',
                    'خطأ في التحقق.',
                    locale
                )
            )

