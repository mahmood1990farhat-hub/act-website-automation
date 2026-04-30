from utils.EMDBase import EMADBaseView
from rest_framework.permissions import IsAuthenticated
from ..serializers import RequestEmailOrPhoneChangeSerializer , ConfirmEmailOrPhoneChangeSerializer
from rest_framework.response import Response
from utils.common import send_verification_code , check_verification_code
from utils.common import remove_empty_values
from rest_framework.exceptions import ValidationError

class RequestEmailOrPhoneChangeView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    def handle_post(self, request):
        data = remove_empty_values(request.data)
        serializer = RequestEmailOrPhoneChangeSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user

        if 'phone_number' in serializer.validated_data:
            new_phone = serializer.validated_data['phone_number']
            user.temp_phone_number = new_phone
            user.phone_verification_in_progress = True
            user.save()
            send_verification_code(new_phone)
            return Response({"detail": "Verification code sent to new phone number."})

        if 'email' in serializer.validated_data:
            new_email = serializer.validated_data['email']
            user.temp_email = new_email
            user.email_verification_in_progress = True
            user.save()
            send_verification_code(user.phone_number) 
            return Response({"detail": "Verification code sent to your phone for email change confirmation."})


class ConfirmEmailOrPhoneChangeView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    def handle_post(self, request):
        serializer = ConfirmEmailOrPhoneChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        code = serializer.validated_data['code']
        target = serializer.validated_data['target']

        phone_to_check = user.temp_phone_number if target == "phone" else user.phone_number

        if not check_verification_code(phone_to_check, code):
            raise ValidationError({"detail": "Invalid or expired verification code."})

        if target == "phone" and user.phone_verification_in_progress:
            user.phone_number = user.temp_phone_number
            user.temp_phone_number = None
            user.phone_verification_in_progress = False
            user.save()
            return Response({"detail": "Phone number updated successfully."})

        if target == "email" and user.email_verification_in_progress:
            user.email = user.temp_email
            user.temp_email = None
            user.email_verification_in_progress = False
            user.save()
            return Response({"detail": "Email updated successfully."})

        raise ValidationError({"detail": "No update is in progress."})


