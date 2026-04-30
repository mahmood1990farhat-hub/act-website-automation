from utils.EMDBase import EMADBaseView
from utils.common import send_verification_code, check_verification_code
from utils.common import phone_number_is_valid
from rest_framework.exceptions import ValidationError
from ..models import CustomUser
from rest_framework import status
from rest_framework.response import Response
from django.utils.translation import gettext as _ 


class SendOTPAPIView(EMADBaseView):
    # def handle_post(self, request):
    #     phone_number = request.data.get('phone_number')
    #     if not phone_number:
    #         raise ValidationError({'details' : _('phone number is required')})
    #     phone_number_is_valid(phone_number=phone_number)
    #     try:
    #         user =  CustomUser.objects.get(phone_number = phone_number)
    #     except CustomUser.DoesNotExist:
    #         raise ValidationError({"details" : _('This number is not registered yet')})

    #     if user.is_active:
    #         raise ValidationError({"details" : _('This number is already activated')})
        
    #     status_result = send_verification_code(phone_number)
    #     return Response({"message": _("Code sent"), "status": status_result}, status=status.HTTP_200_OK)
    pass


class VerifyOTPAPIView(EMADBaseView):
    # def handle_post(self, request):
    #     phone_number = request.data.get('phone_number')
    #     code = request.data.get('code')
    #     if not phone_number or not code:
    #         raise ValidationError({"details": "Phone number and code required"})
        
    #     phone_number_is_valid(phone_number=phone_number)
    #     try:
    #         user =  CustomUser.objects.get(phone_number = phone_number)
    #     except CustomUser.DoesNotExist:
    #         raise ValidationError({"details" : _('This number is not registered yet')})

    #     if user.is_active:
    #         raise ValidationError({"details" : _('This number is already activated')})
        
    #     verified = check_verification_code(phone_number, code)
    #     if verified:
    #         user.is_active = True 
    #         user.save(update_fields = ['is_active'])
    #         return Response({"detail": _("Verified successfully")}, status=status.HTTP_200_OK)
    #     else:
    #         return Response({"detail": _("Incorrect code")}, status=status.HTTP_400_BAD_REQUEST)
    pass

        
