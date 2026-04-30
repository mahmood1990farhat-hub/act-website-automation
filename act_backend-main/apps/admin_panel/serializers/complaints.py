from rest_framework import serializers
from apps.complaints.models import TripComplaint, LostProperty


class AdminTripComplaintResponseSerializer(serializers.Serializer):
    """Serializer for admin to respond to trip complaints"""
    admin_response = serializers.CharField(required=True, allow_blank=False)
    status = serializers.ChoiceField(
        choices=TripComplaint.STATUS_CHOICES,
        required=False
    )


class AdminLostPropertyResponseSerializer(serializers.Serializer):
    """Serializer for admin to respond to lost property reports"""
    admin_notes = serializers.CharField(required=True, allow_blank=False)
    status = serializers.ChoiceField(
        choices=LostProperty.STATUS_CHOICES,
        required=False
    )


class AdminResolveComplaintSerializer(serializers.Serializer):
    """Serializer for admin to resolve complaints"""
    admin_response = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=TripComplaint.STATUS_CHOICES,
        required=False
    )


class AdminResolveLostPropertySerializer(serializers.Serializer):
    """Serializer for admin to resolve lost property"""
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=LostProperty.STATUS_CHOICES,
        required=False
    )

