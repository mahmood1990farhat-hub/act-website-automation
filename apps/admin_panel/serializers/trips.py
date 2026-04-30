from rest_framework import serializers
from apps.trips.models import Trip

class TripWithStopPointSerializer(serializers.ModelSerializer):
    passenger_info = serializers.SerializerMethodField()
    driver_info = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['passenger_info', 'driver_info']

    def get_passenger_info(self, obj):
        if obj.passenger and obj.passenger.user:
            user = obj.passenger.user
            return {
                "full_name": f"{user.first_name} {user.last_name}",
                "phone_number": user.phone_number
            }
        return None

    def get_driver_info(self, obj):
        # Check if it's a guest driver
        if obj.is_guest_driver:
            driver_info = {
                "full_name": obj.guest_driver_name or "Guest Driver",
                "phone_number": obj.guest_driver_phone or "N/A",
                "company": obj.guest_driver_company,
                "is_guest_driver": True
            }
            # Include car info if available
            if obj.guest_driver_car:
                from apps.trips.serializers.guest_driver_car import GuestDriverCarSerializer
                driver_info['car'] = GuestDriverCarSerializer(obj.guest_driver_car).data
            return driver_info
        # System driver
        elif obj.base_driver and obj.base_driver.user:
            user = obj.base_driver.user
            return {
                "full_name": f"{user.first_name} {user.last_name}",
                "phone_number": user.phone_number,
                "is_guest_driver": False
            }
        return None
