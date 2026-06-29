from rest_framework import serializers
from apps.trips.models import Trip
import re


def _format_snapshot_phone(country_code, phone):
    dial_code_match = re.search(r"\+\d+", country_code or "")
    dial_code = dial_code_match.group(0) if dial_code_match else (country_code or "").strip()
    phone_number = (phone or "").strip()
    return " ".join(part for part in [dial_code, phone_number] if part)

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
                "phone_number": user.phone_number,
                "email": user.email,
            }
        if obj.passenger_name or obj.passenger_email or obj.passenger_phone:
            phone = _format_snapshot_phone(obj.passenger_country_code, obj.passenger_phone)
            return {
                "full_name": obj.passenger_name or "Guest Passenger",
                "phone_number": phone or obj.passenger_phone or "",
                "email": obj.passenger_email or "",
                "is_guest_checkout": bool(obj.is_guest_checkout),
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
