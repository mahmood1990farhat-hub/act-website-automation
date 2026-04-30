from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from utils.EMDBase import EMADBaseView
from apps.drivers.models import BaseDriver
from apps.earnings.services.commission_resolver import CommissionResolver
from apps.vehicle.models import VehicleType
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
from django.db import transaction
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class DriverCommissionView(EMADBaseView):
    """
    Get or update driver commission percentage information
    GET /api/admin-panel/drivers/<driver_id>/commission/ - Get commission info
    POST /api/admin-panel/drivers/<driver_id>/commission/ - Update commission percentage
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'post']
    
    def handle_get(self, request, driver_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            driver = BaseDriver.objects.select_related(
                'normal_driver__vehicle__vehicle_type'
            ).get(id=driver_id)
        except BaseDriver.DoesNotExist:
            message = get_bilingual_error_message(
                'Driver not found',
                'السائق غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
        
        # Get vehicle type if driver has one
        vehicle_type = None
        if hasattr(driver, 'normal_driver') and driver.normal_driver.vehicle:
            vehicle_type = driver.normal_driver.vehicle.vehicle_type
        
        # Get effective commission rule
        rule = CommissionResolver.get_commission_rule(
            vehicle_type=vehicle_type,
            driver=driver
        )
        
        # Determine fallback source
        if driver.driver_commission_percentage is not None:
            fallback_source = 'driver'
        elif vehicle_type:
            fallback_source = 'vehicle'
        else:
            fallback_source = 'default'
        
        return Response({
            "success": True,
            "data": {
                "driver_id": driver.id,
                "driver_commission_percentage": float(driver.driver_commission_percentage) if driver.driver_commission_percentage else None,
                "effective_driver_percentage": float(rule.driver_percentage),
                "effective_company_percentage": float(rule.company_percentage),
                "fallback_source": fallback_source,
                "vehicle_type": {
                    "id": vehicle_type.id,
                    "name_en": vehicle_type.name_en,
                    "name_ar": vehicle_type.name_ar
                } if vehicle_type else None
            }
        }, status=status.HTTP_200_OK)


    def handle_post(self, request, driver_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            driver = BaseDriver.objects.get(id=driver_id)
        except BaseDriver.DoesNotExist:
            message = get_bilingual_error_message(
                'Driver not found',
                'السائق غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
        
        # Get percentage from request
        percentage = request.data.get('driver_commission_percentage')
        
        # Validate percentage
        if percentage is None:
            message = get_bilingual_error_message(
                'driver_commission_percentage is required',
                'نسبة العمولة للسائق مطلوبة',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            percentage_decimal = Decimal(str(percentage))
        except (ValueError, TypeError):
            message = get_bilingual_error_message(
                'Invalid percentage format',
                'تنسيق النسبة غير صالح',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        if percentage_decimal < 0 or percentage_decimal > 100:
            message = get_bilingual_error_message(
                'Percentage must be between 0 and 100',
                'يجب أن تكون النسبة بين 0 و 100',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        # Update driver commission percentage
        with transaction.atomic():
            driver.driver_commission_percentage = percentage_decimal
            driver.save()
        
        logger.info(f"Admin {request.user.id} updated driver {driver_id} commission percentage to {percentage_decimal}%")
        
        # Get effective rule for response
        vehicle_type = None
        if hasattr(driver, 'normal_driver') and driver.normal_driver.vehicle:
            vehicle_type = driver.normal_driver.vehicle.vehicle_type
        
        rule = CommissionResolver.get_commission_rule(
            vehicle_type=vehicle_type,
            driver=driver
        )
        
        message = get_bilingual_error_message(
            'Driver commission percentage updated successfully',
            'تم تحديث نسبة عمولة السائق بنجاح',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": {
                "driver_id": driver.id,
                "driver_commission_percentage": float(percentage_decimal),
                "effective_driver_percentage": float(rule.driver_percentage),
                "effective_company_percentage": float(rule.company_percentage),
                "fallback_source": "driver"
            }
        }, status=status.HTTP_200_OK)
