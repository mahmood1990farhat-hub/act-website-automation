from rest_framework import serializers 
from apps.accounts.serializers import CustomUserSerializer , UpdateCustomUserSerializer
from ..models import BaseDriver
from django.db import transaction
from .bank_info import BankDetailsSerializer

class BaseDriverSerializer(serializers.ModelSerializer):
    user_data = serializers.DictField(write_only = True) 
    bank_details_data = serializers.DictField(write_only = True)
    profile = CustomUserSerializer(source ='user' , read_only = True)

    class Meta:
        model = BaseDriver
        fields = ["user_data", "pco", "dbs", "dvla", "bank_details_data" , 'profile']

    def create(self, validated_data):
        user_data = validated_data.pop("user_data")
        user_data["account_type"] = self.context.get('user_type')

        bank_details_data = validated_data.pop('bank_details_data', None)

        with transaction.atomic():
            user_data['is_profile_completed'] = False
            user_data['is_admin_verified'] = False
            user_serializer = CustomUserSerializer(data=user_data)
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()

            if bank_details_data:
                bank_details_serializer = BankDetailsSerializer(data=bank_details_data)
                bank_details_serializer.is_valid(raise_exception=True)
                bank_details = bank_details_serializer.save()
            else:
                bank_details = None

            base_driver = BaseDriver.objects.create(user=user, bank_details=bank_details, **validated_data)
        return base_driver


    def update(self, instance, validated_data):
        bank_data = validated_data.pop('bank_details_data', None)
        user_data = validated_data.pop('user_data' , None)

        if bank_data:
            bank_serializer = BankDetailsSerializer(instance.bank_details, data=bank_data, partial=True)
            bank_serializer.is_valid(raise_exception=True)
            bank_serializer.save()
        
        if user_data:
            user_serializer = UpdateCustomUserSerializer(instance.user , data = user_data , partial=True)
            user_serializer.is_valid(raise_exception= True)
            user_serializer.save()


        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return  instance


        







