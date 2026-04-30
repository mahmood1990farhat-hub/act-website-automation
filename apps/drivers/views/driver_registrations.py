from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from ..serializers import RegisterFullNormalDriverSerializer , NormalDriverUpdateSerializer
from utils.common import  remove_empty_values , get_locale
from django.utils.translation import gettext as _  , activate
from apps.accounts.serializers import CustomUserSerializer
from apps.accounts.permissions import IsNormalDriver
from ..models import NormalDriver



class CreateNormalDriverAccountView(EMADBaseView):
    http_method_names = ['post']
    def handle_post(self, request):
        activate(get_locale(request=request))
        data = remove_empty_values(request.data)
        data['account_type'] = 'normal_driver'
        data['is_profile_completed'] = False
        data['is_admin_verified'] = False
        serialzier = CustomUserSerializer(data = data)
        serialzier.is_valid(raise_exception= True)
        serialzier.save()
        return Response({'message' : _('account created successfully')},  status=status.HTTP_200_OK)


class CompleteNormalDriverInfoView(EMADBaseView):
    http_method_names = ['post']
    permission_classes = [IsAuthenticated]

    def handle_post(self, request):
        activate(get_locale(request=request))
        user = request.user
        user.is_active = True
        
        if hasattr(user, 'base_driver'):
            raise ValidationError({"detail": "This user already has a base driver account."})
        nested_data = self.prepare_data(request.data)
        serializer = RegisterFullNormalDriverSerializer(data=nested_data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        normal_driver = serializer.save()
        return Response({'message' : _('Your information is complete') , 'normal_driver_id': normal_driver.id}, status=201)
        

    def prepare_data(self , data):
        nested_data = {
            "pco": data.get("pco"),
            "dbs": data.get("dbs"),
            "dvla": data.get("dvla"),
            "bank_details_data": {
                "bank_account_number": data.get("bank_account_number"),
                "sort_code": data.get("sort_code"),
                "registered_address": data.get("registered_address"),
                },
            "vehicle_data": {
                "vehicle_number": data.get("vehicle_number"),
                "year_of_manufacture": data.get("year_of_manufacture"),
                "mot": data.get("mot"),
                "phv": data.get("phv"),
                "vehicle_type_id": data.get("vehicle_type") or data.get("vehicle_type_id"),
            },
            "interview_data" : {
                "interview_date" : data.get("interview_date"),
                "interview_time" : data.get("interview_time"),
            }
        }
        return remove_empty_values(nested_data)


class UpdateNormalDriverInfoView(EMADBaseView):
    http_method_names = ['patch']
    permission_classes = [IsNormalDriver]

    def handle_patch(self, request):
        user = request.user

        try:
            normal_driver = user.base_driver.normal_driver
        except (AttributeError, NormalDriver.DoesNotExist):
            raise ValidationError({"detail": "Normal driver not found."})
        
        nested_data = self.prepare_data(request.data)

        serializer = NormalDriverUpdateSerializer(normal_driver, data=nested_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': _('Driver info updated successfully.')})


    def prepare_data(self , data):
        nested= {
            "driver_data":{
            "user_data" : {
                "first_name" : data.get("first_name"),
                "last_name" : data.get("last_name"),
                "address" : data.get("address")
            },
            "pco": data.get("pco"),
            "dbs": data.get("dbs"),
            "dvla": data.get("dvla"),
            "bank_details_data": {
                "bank_account_number": data.get("bank_account_number"),
                "sort_code": data.get("sort_code"),
                "registered_address": data.get("registered_address"),
                }
            },
            
            "vehicle_data": {
                "vehicle_number": data.get("vehicle_number"),
                "year_of_manufacture": data.get("year_of_manufacture"),
                "mot": data.get("mot"),
                "phv": data.get("phv"),
                "vehicle_type_id": data.get("vehicle_type") or data.get("vehicle_type_id"),
            }
        }
        return remove_empty_values(nested)


        

