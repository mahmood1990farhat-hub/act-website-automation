from ..models import BankDetails
from rest_framework import serializers

class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = ['bank_account_number' , 'sort_code' , 'registered_address']
