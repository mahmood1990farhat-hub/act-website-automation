from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsOfficeOwner
from ..models import Office
from rest_framework.exceptions import ValidationError
from apps.drivers.serializers import OfficeDriverSerializer
from rest_framework.response import Response
from rest_framework import status
from utils.common import extract_clean_data_from_request
from django.utils.translation import gettext as _ 


class OfficeDriverView(EMADBaseView):
    permission_classes = [IsOfficeOwner]
    http_method_names = ['get' , 'post']

    def handle_post(self, request):
        user = request.user
        try:
            office = user.office
        except Office.DoesNotExist:
            raise ValidationError({"details" : "No office is associated with this user."})
        
        flat_data = extract_clean_data_from_request(request=request)
        nested_data = self.prepare_data(flat_data)
        serializer = OfficeDriverSerializer(data=  nested_data , context ={'office' : office})
        serializer.is_valid(raise_exception= True )
        serializer.save()
        return Response({"message" : _("Driver created successfully")} , status=status.HTTP_200_OK)


    def prepare_data(self , data):
        return {
            "driver_data": {
                "user_data": {
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "email": data.get("email"),
                    "phone_number": data.get("phone_number"),
                    "address": data.get("address"),
                    "password": data.get("password"),
                    "confirm_password": data.get("confirm_password"),
                },
                "pco": data.get("pco"),
                "dbs": data.get("dbs"),
                "dvla": data.get("dvla"),
                "bank_details_data": {
                    "bank_account_number": data.get("bank_account_number"),
                    "sort_code": data.get("sort_code"),
                    "registered_address": data.get("registered_address"),
                }
            }
        }


    def handle_get(self, request):
        user = request.user
        try:
            office = user.office
        except Office.DoesNotExist:
            raise ValidationError({"details" : "No office is associated with this user."})
        drivers = office.office_drivers.select_related('driver__user').all()
        serialzier = OfficeDriverSerializer(drivers , many= True , context = {'request' : request})
        return Response(serialzier.data , status=status.HTTP_200_OK)

  