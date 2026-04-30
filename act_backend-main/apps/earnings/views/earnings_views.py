from rest_framework.response import Response
from rest_framework import status
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsVerifiedAndProfileCompleted, IsNormalDriver
from django.db.models import Sum
from apps.earnings.models import DriverEarningLedger
from apps.earnings.serializers import DriverEarningPublicSerializer
from utils.common import get_locale
from django.utils.translation import activate


class DriverEarningsView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        driver = request.user.base_driver
        if not driver:
            from utils.common.error_handlers import create_error_response, get_bilingual_error_message
            message = get_bilingual_error_message(
                'Driver profile not found',
                'ملف السائق غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        earnings = DriverEarningLedger.objects.filter(driver=driver).select_related('trip', 'trip__car_type')
        
        # Use net_amount for all calculations (driver only sees their earnings)
        total_earned = earnings.aggregate(total=Sum('net_amount'))['total'] or 0
        available_for_payout = earnings.filter(status='AVAILABLE').aggregate(total=Sum('net_amount'))['total'] or 0
        pending = earnings.filter(status='PENDING').aggregate(total=Sum('net_amount'))['total'] or 0
        paid = earnings.filter(status='PAID').aggregate(total=Sum('net_amount'))['total'] or 0
        
        return Response({
            "success": True,
            "data": {
                "total_earned": float(total_earned),
                "available_for_payout": float(available_for_payout),
                "pending": float(pending),
                "paid": float(paid),
                "earnings": DriverEarningPublicSerializer(earnings, many=True, context={'request': request}).data
            }
        }, status=status.HTTP_200_OK)

