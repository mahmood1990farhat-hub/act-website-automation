from rest_framework import serializers
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    trips_count = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "account_type",
            "address",
            "is_active",
            "is_profile_completed",
            "is_admin_verified",
            "trips_count",
            'date_joined'
        ]
        read_only_fields = ["id", "is_active"]

    def get_trips_count(self, obj):
        if obj.account_type == 'passenger' and hasattr(obj, 'passenger_profile') and obj.passenger_profile:
            return obj.passenger_profile.trips.count()
        elif obj.account_type == 'normal_driver' and hasattr(obj, 'base_driver') and obj.base_driver:
            return obj.base_driver.trips.count()
        return 0
