from rest_framework import serializers
from apps.earnings.models import (
    DriverEarningLedger,
    CompanyRevenueLedger,
    DriverRefundLedger,
    CompanyRefundLedger,
    PayoutBatch,
    CommissionRule
)
from apps.trips.serializers import TripWithStopPointBasicSerializer


class TripBasicForEarningsSerializer(serializers.ModelSerializer):
    """Trip serializer for driver earnings - excludes cost and other sensitive info"""
    car_type = serializers.SerializerMethodField()
    
    class Meta:
        from apps.trips.models import Trip
        model = Trip
        fields = [
            'id',
            'pickup_lat',
            'pickup_lng',
            'pickup_str',
            'dropoff_lat',
            'dropoff_lng',
            'dropoff_str',
            'trip_date',
            'trip_time',
            'car_type',
            'status',
            'passengers_count',
        ]
        read_only_fields = fields
    
    def get_car_type(self, obj):
        """Return car_type basic info without cost"""
        if not obj.car_type:
            return None
        return {
            'id': obj.car_type.id,
            'name_en': obj.car_type.name_en,
            'name_ar': obj.car_type.name_ar,
        }


class DriverEarningPublicSerializer(serializers.ModelSerializer):
    """Public serializer for driver earnings - hides commission details"""
    trip = TripBasicForEarningsSerializer(read_only=True)
    amount = serializers.DecimalField(source='net_amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = DriverEarningLedger
        fields = [
            'id',
            'trip',
            'amount',
            'currency',
            'status',
            'created_at',
            'paid_at',
        ]
        read_only_fields = fields


class DriverEarningSerializer(serializers.ModelSerializer):
    trip = TripWithStopPointBasicSerializer(read_only=True)
    
    class Meta:
        model = DriverEarningLedger
        fields = [
            'id',
            'trip',
            'gross_amount',
            'commission_amount',
            'net_amount',
            'currency',
            'status',
            'stripe_transfer_id',
            'created_at',
            'paid_at',
        ]
        read_only_fields = fields


class CompanyRevenueSerializer(serializers.ModelSerializer):
    trip = TripWithStopPointBasicSerializer(read_only=True)
    
    class Meta:
        model = CompanyRevenueLedger
        fields = [
            'id',
            'trip',
            'amount',
            'currency',
            'created_at',
        ]
        read_only_fields = fields


class DriverRefundSerializer(serializers.ModelSerializer):
    trip = TripWithStopPointBasicSerializer(read_only=True)
    
    class Meta:
        model = DriverRefundLedger
        fields = [
            'id',
            'trip',
            'refund_amount',
            'currency',
            'refund_rule',
            'stripe_refund_id',
            'created_at',
        ]
        read_only_fields = fields


class CommissionRuleSerializer(serializers.ModelSerializer):
    vehicle_type_name = serializers.CharField(source='vehicle_type.name_en', read_only=True)
    
    class Meta:
        model = CommissionRule
        fields = [
            'id',
            'vehicle_type',
            'vehicle_type_name',
            'company_percentage',
            'driver_percentage',
            'is_active',
            'created_at',
        ]


class PayoutBatchSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.email', read_only=True)
    
    class Meta:
        model = PayoutBatch
        fields = [
            'id',
            'batch_id',
            'status',
            'total_amount',
            'currency',
            'total_earnings',
            'successful_transfers',
            'failed_transfers',
            'created_by',
            'created_by_name',
            'created_at',
            'completed_at',
            'error_log',
        ]
        read_only_fields = fields

