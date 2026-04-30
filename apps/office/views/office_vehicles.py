from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsOfficeOwner
from ..models import Office
from rest_framework.exceptions import ValidationError
from apps.vehicle.serializers import OfficeVehicleSerializer
from rest_framework.response import Response
from rest_framework import status
from utils.common import extract_clean_data_from_request
from django.utils.translation import gettext as _  


class OfficeVehiclesView(EMADBaseView):
    permission_classes = [IsOfficeOwner]
    http_method_names = ['post',  'get']

    def handle_get(self, request):
        user = request.user
        try:
            office = user.office
        except Office.DoesNotExist:
            raise ValidationError({"details" : "No office is associated with this user."})
        office_vehicles = office.office_vehicles.select_related('vehicle').all()
        serializer = OfficeVehicleSerializer(office_vehicles , many=  True , context = {'request' : request})
        return Response(serializer.data , status=status.HTTP_200_OK)

    def handle_post(self , request):
        user = request.user
        try:
            office = user.office
        except Office.DoesNotExist:
            raise ValidationError({"details" : "No office is associated with this user."})
        
        flat_data = extract_clean_data_from_request(request=request)
        nested_data = self.prepare_data(flat_data)
        serializer = OfficeVehicleSerializer(data=  nested_data , context ={'office' : office})
        serializer.is_valid(raise_exception= True )
        serializer.save()
        return Response({"message" : _("Vehicle created successfully")} , status=status.HTTP_200_OK)

    def prepare_data(self , data):
        return {
            "vehicle_data" : {
                'vehicle_number' : data.get('vehicle_number'),
                'mot' : data.get('mot'),
                'year_of_manufacture' : data.get('year_of_manufacture'),
                'phv' : data.get('phv'),
                'vehicle_type' : data.get('vehicle_type')
            }
        }

