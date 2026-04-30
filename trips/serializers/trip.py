
from rest_framework import serializers
from ..models import Trip , StopPoint
from utils.common import is_past_datetime , get_route_with_distance  , reverse_geocode
from utils.calculate_cost import calculate_total_cost
from django.utils.translation import gettext as _
from .stop_points import StopPointSerializer
from .airport import AirportSerializer
from .guest_driver_car import GuestDriverCarSerializer
from apps.vehicle.serializers import VehicleSerializer
from apps.earnings.services.commission_resolver import CommissionResolver
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from decimal import Decimal
class TripSerializer(serializers.ModelSerializer):
    stop_points = StopPointSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = [
            'id', 'status', 'created_at', 'cost', 'route_polyline', 'is_paid', 
            'stripe_payment_intent', 'expected_trip_duration_minutes', 'distance_miles', 
            'passenger', 'base_driver', 'office',
            'cancelled_by_driver', 'cancellation_reason', 'cancelled_at'  # Read-only cancellation fields
        ]
        extra_kwargs = {
            'car_type': {'required': False, 'allow_null': True},
            'cost': {'required': False},  # Cost is calculated, not provided
            'is_guest_driver': {'required': False},
            'guest_driver_name': {'required': False, 'allow_blank': True, 'allow_null': True},
            'guest_driver_phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'guest_driver_company': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def create(self, validated_data):
        request = self.context.get('request')
        locale = self.context.get('locale', 'en')
        stop_points = validated_data.pop('stop_points', [])

        # Only validate if we're actually creating a trip (not just calculating cost)
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self._validate_trip_datetime(validated_data, request)
            self._validate_passenger_count(validated_data)
            validated_data['passenger'] = request.user.passenger_profile
        else:
            # For cost calculation, skip passenger validation
            # car_type is optional for cost calculation
            pass

        validated_data['route_polyline'], validated_data['cost'] = self._process_trip_data(validated_data, stop_points)
        self._enrich_address_info(validated_data, locale)

        trip = super().create(validated_data)
        self._create_stop_points(trip, stop_points)
        return trip

    def _validate_trip_datetime(self, data, request):
        trip_date = data.get("trip_date")
        trip_time = data.get("trip_time")
        if is_past_datetime(
            date_str=trip_date.strftime("%Y-%m-%d"),
            time_str=trip_time.strftime("%H:%M"),
            request=request
        ):
            raise serializers.ValidationError({"details": _("Time and date in the past")})

    def _validate_passenger_count(self, data):
        car_type = data.get('car_type')
        passengers_count = data.get('passengers_count')
        if not car_type:
            raise serializers.ValidationError({"details": _("You must choose the type of vehicle.")})
        if passengers_count and passengers_count > car_type.max_passengers_count:
            raise serializers.ValidationError({
                'passengers_count': _(
                    f"Passengers count ({passengers_count}) exceeds max capacity for car type '{car_type.name_en}' ({car_type.max_passengers_count})."
                )
            })

    def _process_trip_data(self, data, stop_points):
        result = get_route_with_distance(
            pickup_lat=data['pickup_lat'],
            pickup_lng=data['pickup_lng'],
            dropoff_lat=data['dropoff_lat'],
            dropoff_lng=data['dropoff_lng'],
            stop_points=stop_points
        )
        data['distance_miles'] = result['distance_miles']
        data['expected_trip_duration_minutes'] = result['duration_minutes']
        
        # For cost calculation, car_type might not be provided
        # Return a default cost of 0 if car_type is missing
        trip_time = data['trip_time']
        trip_date = data.get('trip_date')
        car_type = data.get('car_type')
        if car_type:
            total_cost, *_ = calculate_total_cost(
                trip_time,
                car_type.name_en,
                result['distance_miles'],
                pickup_lat=data['pickup_lat'],
                pickup_lng=data['pickup_lng'],
                dropoff_lat=data['dropoff_lat'],
                dropoff_lng=data['dropoff_lng'],
                manual_airport_id=data.get('airport'),
                trip_date=trip_date,
            )
        else:
            # If no car_type, return 0 cost (will be calculated separately in view)
            total_cost = 0

        return result['route_polyline'], total_cost

    def _enrich_address_info(self, data, locale):
        direction = data.get('airport_direction')
        if direction == 'from':
            coords = (data['dropoff_lat'], data['dropoff_lng'])
            prefix = 'dropoff'
        elif direction == 'to':
            coords = (data['pickup_lat'], data['pickup_lng'])
            prefix = 'pickup'
        else:
            return

        address_data = reverse_geocode(*coords, locale)
        if address_data:
            data[f'{prefix}_str'] = address_data['formatted_address']
            data[f'{prefix}_postal_code'] = address_data['postal_code']
            data[f'{prefix}_place_id'] = address_data['place_id']

    def _create_stop_points(self, trip, stop_points):
        for stop in stop_points:
            StopPoint.objects.create(trip=trip, **stop)

    # inside TripSerializer.validate  (or view if you prefer)
    def validate(self, attrs):
        passengers = attrs.get('passengers_count', 0)
        large      = attrs.get('large_suitcase', 0)
        small      = attrs.get('small_suitcase', 0)
        suitcases  = large + small
        
        if passengers > 7:
            raise serializers.ValidationError({
                "details": _(
                    "Our online pricing supports up to 7 passengers. "
                    "You selected %(count)s passengers, so please contact us directly at "
                    "07464 940 000 to complete your booking."
                ) % {"count": passengers},
            })

        if suitcases > 8:
            raise serializers.ValidationError({
                "details": _(
                    "We're sorry, but online bookings must be made at least 3 hours in advance. "
                    "You selected %(large)s large + %(small)s small = %(total)s suitcases, "
                    "so please contact us directly at 07464 940 000 to complete your booking."
                ) % {"large": large, "small": small, "total": suitcases},
            })

        # Validate 24-hour advance booking requirement
        trip_date = attrs.get('trip_date')
        trip_time = attrs.get('trip_time')
        
        if trip_date and trip_time:
            try:
                # Ensure they are date and time objects (DRF should convert them, but handle both cases)
                if isinstance(trip_date, str):
                    from django.utils.dateparse import parse_date
                    trip_date = parse_date(trip_date)
                if isinstance(trip_time, str):
                    from django.utils.dateparse import parse_time
                    trip_time = parse_time(trip_time)
                
                # Only validate if we have valid date and time objects
                if trip_date and trip_time and isinstance(trip_date, date) and isinstance(trip_time, time):
                    departure = timezone.make_aware(
                        datetime.combine(trip_date, trip_time)
                    )
                    now = timezone.now()
                    gap = departure - now

                    if gap < timedelta(hours=3):
                        hours, remainder = divmod(int(gap.total_seconds()), 3600)
                        minutes = remainder // 60
                        raise serializers.ValidationError({
                            "details": _(
                                "We're sorry, but online bookings must be made at least 3 hours in advance. "
                                "To arrange a last-minute trip, please contact us directly at 07464 940 000."
                            ),
                        })
            except (ValueError, TypeError, AttributeError) as e:
                # If date/time parsing or conversion fails, let DRF handle the field validation error
                # Don't raise here - let field-level validation handle it
                pass
            except serializers.ValidationError:
                # Re-raise ValidationError
                raise
            except Exception as e:
                # Convert any other exception to ValidationError to prevent 500 errors
                raise serializers.ValidationError({
                    "details": _("Error validating trip date and time. Please check your input.")
                })

        return attrs


class TripWithStopPointBasicSerializer(serializers.ModelSerializer):
    stop_points = StopPointSerializer(many=True, read_only=True)
    airport_info = AirportSerializer(source='airport', read_only=True)
    # Override passenger and car_type to return full objects instead of IDs
    passenger = serializers.SerializerMethodField()
    car_type = serializers.SerializerMethodField()
    cancelled_by_driver = serializers.SerializerMethodField()
    # When context['for_driver'] is true: estimate driver share using CommissionResolver + base_driver
    driver_earnings = serializers.SerializerMethodField()
    driver_commission_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'

    def _base_driver_for_commission(self):
        ctx = self.context or {}
        driver = ctx.get('base_driver')
        if driver is not None:
            return driver
        request = ctx.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            return getattr(request.user, 'base_driver', None)
        return None

    def get_driver_earnings(self, obj):
        if not (self.context or {}).get('for_driver'):
            return None
        driver = self._base_driver_for_commission()
        if driver is None or obj.cost is None:
            return None

        rule = CommissionResolver.get_commission_rule(
            vehicle_type=obj.car_type,
            driver=driver,
        )
        share = (
            Decimal(str(obj.cost))
            * (rule.driver_percentage / Decimal('100'))
        ).quantize(Decimal('0.01'))
        return str(share)

    def get_driver_commission_percentage(self, obj):
        if not (self.context or {}).get('for_driver'):
            return None
        driver = self._base_driver_for_commission()
        if driver is None:
            return None

        rule = CommissionResolver.get_commission_rule(
            vehicle_type=obj.car_type,
            driver=driver,
        )
        return float(rule.driver_percentage)

    def get_passenger(self, obj):
        """Return passenger full information instead of just ID"""
        if not obj.passenger:
            return None
        
        user = getattr(obj.passenger, 'user', None)
        if not user:
            return None
        
        return {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
            }
    
    def get_car_type(self, obj):
        """Return car_type full information instead of just ID"""
        if not obj.car_type:
            return None
        
        from apps.vehicle.serializers import VehicleTypeSerializer
        return VehicleTypeSerializer(obj.car_type).data
    
    def get_cancelled_by_driver(self, obj):
        """Return full driver information who cancelled the trip, or None"""
        if not obj.cancelled_by_driver_id:
            return None
        
        driver = obj.cancelled_by_driver_id
        user = getattr(driver, 'user', None)
        if not user:
            return None
        
        return {
            "id": driver.id,
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number
            }
        }


class TripWithStopPointSerializer(serializers.ModelSerializer):
    stop_points = StopPointSerializer(many=True, read_only=True)

    airport_info = AirportSerializer(source='airport', read_only=True)
    passenger_info = serializers.SerializerMethodField()
    driver_info = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    cancelled_by_driver = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        extra_fields = ['airport_info', 'passenger_info', 'driver_info', 'vehicle_info', 'cancelled_by_driver']

    def get_account_type(self):
        return self.context.get("account_type")

    def get_passenger_info(self, obj):
        if self.get_account_type() != 'normal_driver':
            return None
        user = getattr(obj.passenger, 'user', None)
        if user:
            return {
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        return None

    def get_driver_info(self, obj):
        if self.get_account_type() != 'passenger':
            return None
        if getattr(obj, 'is_guest_driver', False):
            name = (obj.guest_driver_name or '').strip()
            if name:
                parts = name.split(None, 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ''
            else:
                first_name, last_name = 'Guest', 'Driver'
            return {
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': obj.guest_driver_phone or '',
                'company': obj.guest_driver_company or '',
                'is_guest_driver': True,
            }
        user = getattr(obj.base_driver, 'user', None) if obj.base_driver_id else None
        if user:
            return {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number' : user.phone_number,
                'is_guest_driver': False,
            }
        return None

    def get_vehicle_info(self, obj):
        if self.get_account_type() != 'passenger':
            return None
        if getattr(obj, 'is_guest_driver', False) and obj.guest_driver_car_id and obj.guest_driver_car:
            return GuestDriverCarSerializer(obj.guest_driver_car).data
        if not obj.base_driver_id:
            return None
        try:
            vehicle = obj.base_driver.normal_driver.vehicle
            return VehicleSerializer(vehicle).data if vehicle else None
        except AttributeError:
            return None

    def get_cancelled_by_driver(self, obj):
        """Return full driver information who cancelled the trip, or None"""
        if not obj.cancelled_by_driver_id:
            return None
        
        driver = obj.cancelled_by_driver_id
        user = getattr(driver, 'user', None)
        if not user:
            return None
        
        return {
            "id": driver.id,
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number
            }
        }




