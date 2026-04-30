"""
Detail serializers for admin panel - comprehensive information for passengers and drivers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.passengers.models import Passenger
from apps.drivers.models import NormalDriver, BaseDriver
from apps.trips.models import Trip
from apps.complaints.models import TripComplaint, Complaint
from .custom_users import CustomUserSerializer
from .driver import NormalDriverSerializer, BaseDriverSerializer
from apps.trips.serializers import TripWithStopPointBasicSerializer

User = get_user_model()


class PassengerDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for passenger details"""
    user = CustomUserSerializer(read_only=True)
    trips = serializers.SerializerMethodField()
    trips_count = serializers.SerializerMethodField()
    complaints_count = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    recent_trips = serializers.SerializerMethodField()
    
    class Meta:
        model = Passenger
        fields = [
            'id',
            'user',
            'trips',
            'trips_count',
            'complaints_count',
            'total_spent',
            'recent_trips',
        ]
    
    def get_trips(self, obj):
        """Get all trips for this passenger"""
        trips = obj.trips.all().select_related(
            'base_driver__user',
            'car_type',
            'airport'
        ).prefetch_related('stop_points').order_by('-created_at')
        ctx = {**(self.context or {}), 'for_driver': False}
        return TripWithStopPointBasicSerializer(trips, many=True, context=ctx).data
    
    def get_trips_count(self, obj):
        """Get total trips count"""
        return obj.trips.count()
    
    def get_complaints_count(self, obj):
        """Get total complaints count"""
        user = obj.user
        trip_complaints = TripComplaint.objects.filter(trip__passenger=obj).count()
        normal_complaints = Complaint.objects.filter(user=user).count()
        return trip_complaints + normal_complaints
    
    def get_total_spent(self, obj):
        """Get total amount spent on completed trips"""
        from django.db.models import Sum
        total = obj.trips.filter(
            status='completed',
            is_paid=True
        ).aggregate(total=Sum('cost'))['total']
        return float(total) if total else 0.0
    
    def get_recent_trips(self, obj):
        """Get recent 5 trips"""
        recent = obj.trips.all().select_related(
            'base_driver__user',
            'car_type'
        ).order_by('-created_at')[:5]
        ctx = {**(self.context or {}), 'for_driver': False}
        return TripWithStopPointBasicSerializer(recent, many=True, context=ctx).data


class DriverDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for driver details"""
    driver = BaseDriverSerializer(read_only=True)
    vehicle = serializers.SerializerMethodField()
    trips = serializers.SerializerMethodField()
    trips_count = serializers.SerializerMethodField()
    total_earnings = serializers.SerializerMethodField()
    recent_trips = serializers.SerializerMethodField()
    onboarding_status = serializers.SerializerMethodField()
    complaints_count = serializers.SerializerMethodField()
    driver_commission_percentage = serializers.SerializerMethodField()
    effective_commission_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = NormalDriver
        fields = [
            'id',
            'driver',
            'vehicle',
            'trips',
            'trips_count',
            'total_earnings',
            'recent_trips',
            'onboarding_status',
            'complaints_count',
            'driver_commission_percentage',
            'effective_commission_percentage',
        ]
    
    def get_vehicle(self, obj):
        """Get vehicle information"""
        from .vehicles import VehicleSerializer
        if obj.vehicle:
            return VehicleSerializer(obj.vehicle, context=self.context).data
        return None
    
    def get_trips(self, obj):
        """Get all trips for this driver"""
        trips = obj.driver.trips.all().select_related(
            'passenger__user',
            'car_type',
            'airport'
        ).prefetch_related('stop_points').order_by('-created_at')
        ctx = {
            **(self.context or {}),
            'for_driver': True,
            'base_driver': obj.driver,
        }
        return TripWithStopPointBasicSerializer(trips, many=True, context=ctx).data
    
    def get_trips_count(self, obj):
        """Get total trips count"""
        return obj.driver.trips.count()
    
    def get_total_earnings(self, obj):
        """Get total earnings from completed trips"""
        from django.db.models import Sum
        total = obj.driver.trips.filter(
            status='completed',
            is_paid=True
        ).aggregate(total=Sum('cost'))['total']
        return float(total) if total else 0.0
    
    def get_recent_trips(self, obj):
        """Get recent 5 trips"""
        recent = obj.driver.trips.all().select_related(
            'passenger__user',
            'car_type'
        ).order_by('-created_at')[:5]
        ctx = {
            **(self.context or {}),
            'for_driver': True,
            'base_driver': obj.driver,
        }
        return TripWithStopPointBasicSerializer(recent, many=True, context=ctx).data
    
    def get_onboarding_status(self, obj):
        """Get onboarding request status if exists"""
        try:
            onboarding_request = obj.driver.user.driver_onboarding_request
            return {
                'id': onboarding_request.id,
                'status': onboarding_request.status,
                'status_display': onboarding_request.get_status_display(),
                'created_at': onboarding_request.created_at,
                'reviewed_at': onboarding_request.reviewed_at,
                'admin_notes': onboarding_request.admin_notes,
            }
        except Exception:
            return None
    
    def get_complaints_count(self, obj):
        """Get total complaints count"""
        user = obj.driver.user
        trip_complaints = TripComplaint.objects.filter(trip__base_driver=obj.driver).count()
        normal_complaints = Complaint.objects.filter(user=user).count()
        return trip_complaints + normal_complaints
    
    def get_driver_commission_percentage(self, obj):
        """Get driver's custom commission percentage"""
        if obj.driver.driver_commission_percentage is not None:
            return float(obj.driver.driver_commission_percentage)
        return None
    
    def get_effective_commission_percentage(self, obj):
        """Get effective commission percentage (with fallback source)"""
        from apps.earnings.services.commission_resolver import CommissionResolver
        
        vehicle_type = None
        if obj.vehicle:
            vehicle_type = obj.vehicle.vehicle_type
        
        rule = CommissionResolver.get_commission_rule(
            vehicle_type=vehicle_type,
            driver=obj.driver
        )
        
        # Determine fallback source
        if obj.driver.driver_commission_percentage is not None:
            fallback_source = 'driver'
        elif vehicle_type:
            fallback_source = 'vehicle'
        else:
            fallback_source = 'default'
        
        return {
            'driver_percentage': float(rule.driver_percentage),
            'company_percentage': float(rule.company_percentage),
            'fallback_source': fallback_source
        }

