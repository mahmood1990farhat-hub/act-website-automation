from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..serializers import PassengerSerializer
from utils.common import  remove_empty_values , get_locale
from django.utils.translation import gettext as _  , activate
from apps.accounts.serializers import UpdateCustomUserSerializer
from apps.accounts.permissions import IsPassenger


class RegisterPassengerView(EMADBaseView):
    http_method_names = ['post']
    permission_classes = [AllowAny]

    def handle_post(self, request):
        activate(get_locale(request=request))
        data = remove_empty_values(request.data)
        serializer = PassengerSerializer(data = data)
        serializer.is_valid(raise_exception= True)
        serializer.save()
        return Response({"message": "Done"} , status=status.HTTP_200_OK)
        


class UpdatePassengerView(EMADBaseView):
    permission_classes = [IsPassenger]
    http_method_names = ['patch']

    def handle_patch(self, request):
        activate(get_locale(request=request))
        data = remove_empty_values(request.data)
        user = request.user
        serializer = UpdateCustomUserSerializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": _("Account updated successfully")}, status=status.HTTP_200_OK)
    

