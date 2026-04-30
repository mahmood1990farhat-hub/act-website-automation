from rest_framework import serializers
from apps.drivers.models import NormalDriver ,  BaseDriver ,BankDetails
from .custom_users import CustomUserSerializer
from .vehicles import VehicleSerializer

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = '__all__'

class BaseDriverSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer()
    bank_details = BankDetailsSerializer()

    class Meta:
        model = BaseDriver
        fields = ['id', 'user', 'pco', 'dbs', 'dvla', 'bank_details']


class NormalDriverSerializer(serializers.ModelSerializer):
    driver = BaseDriverSerializer()
    vehicle = VehicleSerializer()

    class Meta:
        model = NormalDriver
        fields = ['id', 'driver', 'vehicle']
