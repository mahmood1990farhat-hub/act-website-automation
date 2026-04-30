from datetime import time 
from rest_framework.exceptions import ValidationError


PRICING = {
    "Standard PHV": {
        "normal": [
            (10, 4.60),
            (20, 3.68),
            (30, 3.31),
            (40, 2.82),
            (50, 2.67),
            (60, 2.41),
            (70, 2.29),
            (80, 2.17),
            (90, 2.06),
        ],
        "peak": [
            (10, 4.90),
            (20, 3.92),
            (30, 3.33),
            (40, 2.83),
            (50, 2.69),
            (60, 2.42),
            (70, 2.30),
            (80, 2.19),
            (90, 2.08),
        ]
    },
    "7 Seaters PHV": {
        "normal": [
            (10, 5.50),
            (20, 4.40),
            (30, 3.74),
            (40, 3.18),
            (50, 2.86),
            (60, 2.57),
            (70, 2.45),
            (80, 2.32),
            (90, 2.21),
        ],
        "peak": [
            (10, 5.70),
            (20, 4.56),
            (30, 3.88),
            (40, 3.29),
            (50, 2.97),
            (60, 2.67),
            (70, 2.54),
            (80, 2.41),
            (90, 2.29),
        ]
    },
    "Luxury": {
        "normal": [
            (10, 15.00),
            (20, 12.00),
            (30, 10.20),
            (40, 8.67),
            (50, 7.80),
            (60, 7.02),
            (70, 6.67),
            (80, 6.34),
            (90, 6.02),
        ],
        "peak": [
            (10, 16.00),
            (20, 12.80),
            (30, 10.88),
            (40, 9.25),
            (50, 8.32),
            (60, 7.49),
            (70, 7.12),
            (80, 6.67),
            (90, 6.42),
        ]
    },
    "Luxury Van": {
        "normal": [
            (10, 12.00),
            (20, 9.60),
            (30, 8.16),
            (40, 6.94),
            (50, 6.24),
            (60, 5.62),
            (70, 5.34),
            (80, 5.07),
            (90, 4.82),
        ],
        "peak": [
            (10, 13.00),
            (20, 9.10),
            (30, 7.74),
            (40, 6.57),
            (50, 5.92),
            (60, 5.33),
            (70, 5.06),
            (80, 4.81),
            (90, 4.57),
        ]
    },
    'VIP Business PHV':{
        "normal": [
            (10, 35.00),
            (20, 28.00),
            (30, 23.80),
            (40, 20.23),
            (50, 18.21),
            (60, 16.39),
            (70, 15.57),
            (80, 14.79),
            (90, 14.05),
        ],
        "peak": [
            (10, 37.00),
            (20, 25.90),
            (30, 22.02),
            (40, 18.71),
            (50, 16.84),
            (60, 15.16),
            (70, 14.40),
            (80, 13.68),
            (90, 13.00),
        ]
    },
}



MIN_FARE = 40.00

def _apply_minimum_fare(subtotal):
    if subtotal >= MIN_FARE:
        return subtotal, 0
    return MIN_FARE, MIN_FARE - subtotal


def get_rate_per_mile(car_type, distance_miles, is_peak):
    if car_type not in PRICING:
        raise ValidationError({"details" : "Unsupported car type"})

    time_type = "peak" if is_peak else "normal"
    pricing_list = PRICING[car_type][time_type]

    for max_distance, rate in pricing_list:
        if distance_miles < max_distance:
            return rate

    raise ValueError("No rate found")  # Should not happen


def calculate_trip_cost(trip_time, car_type, distance_miles):
    """
    Calculate the total cost of a trip based on time, car type, and distance.

    Parameters:
    ----------
    trip_time : datetime.time
        The time the trip starts. Used to determine if the trip is during peak hours.
    car_type : str
        Type of car used for the trip. Supported types: "standard", "luxury" , "van".
    distance_miles : float
        The total distance of the trip in miles.

    Returns:
    -------
    float
        The total trip cost, rounded to 2 decimal places.

    Notes:
    -----
    - Peak hours are defined as 07:00–10:00 and 16:00–19:00.
    - Pricing per mile varies by car type, distance range, and whether the trip occurs during peak hours.
    - Raises ValueError if the car type is not supported.
    """
    is_peak = (
        time(7, 0) <= trip_time <= time(10, 0) or
        time(16, 0) <= trip_time <= time(19, 0)
    )

    rate_per_mile = get_rate_per_mile(car_type, distance_miles, is_peak)
    trip_cost = round(rate_per_mile * distance_miles, 2)
    return trip_cost


def calculate_vat(cost):
    """
    Calculate the VAT amount and the total cost including 20% VAT.

    Args:
        cost (float): The original cost without VAT.

    Returns:
        tuple: (vat_amount, total_cost_with_vat)
    """
    vat = cost * 0.20
    total = cost + vat
    return vat, total

def calculate_airport_vat(cost, pickup_airport=None, dropoff_airport=None):
    """
    Calculate the total cost including fixed airport VAT amount
    بناءً على وجود مطار في نقطة الانطلاق أو الوصول (أو كليهما).

    Args:
        cost (Decimal or float): The original cost before VAT.
        pickup_airport (Airport | None): مطار نقطة الانطلاق إن وُجد.
        dropoff_airport (Airport | None): مطار نقطة الوصول إن وُجد.

    Returns:
        Decimal: (vat_amount, total_cost_after_airport_vat)
    """
    vat_amount = 0
    # إذا كان هناك مطار عند نقطة الانطلاق أضف pickup_vat
    if pickup_airport:
        vat_amount += pickup_airport.pickup_vat
    # إذا كان هناك مطار عند نقطة الوصول أضف dropoff_vat
    if dropoff_airport:
        vat_amount += dropoff_airport.dropoff_vat

    return vat_amount, cost + vat_amount

def _calculate_total_cost_legacy(
    trip_time_obj,
    car_type_name_en,
    distance_miles,
    pickup_lat=None,
    pickup_lng=None,
    dropoff_lat=None,
    dropoff_lng=None,
    trip_date=None,
):
    """
    Legacy hardcoded pricing calculation.
    Used when dynamic pricing is disabled.
    """
    base_trip_cost = calculate_trip_cost(trip_time_obj, car_type_name_en, distance_miles)
    regular_vat, cost_with_vat = calculate_vat(base_trip_cost)

    # اكتشاف المطارات من الإحداثيات إن وُجدت
    pickup_airport = None
    dropoff_airport = None
    try:
        if (
            pickup_lat is not None and pickup_lng is not None and
            dropoff_lat is not None and dropoff_lng is not None
        ):
            from apps.pricing.services.airport_resolver import AirportResolver

            airport_info = AirportResolver.detect_airport(
                pickup_lat,
                pickup_lng,
                dropoff_lat,
                dropoff_lng,
            )
            pickup_airport = airport_info.get("pickup_airport")
            dropoff_airport = airport_info.get("dropoff_airport")
    except Exception:
        # في حال حدوث أي خطأ في اكتشاف المطار نستمر بدون رسوم مطار
        pickup_airport = None
        dropoff_airport = None

    airport_vat, subtotal = calculate_airport_vat(
        cost_with_vat,
        pickup_airport=pickup_airport,
        dropoff_airport=dropoff_airport,
    )

    total_cost, min_adjustment = _apply_minimum_fare(subtotal)

    return (round(total_cost, 2),
            round(regular_vat, 2),
            round(airport_vat, 2),
            round(base_trip_cost, 2),
            round(min_adjustment, 2))


def calculate_total_cost(
    trip_time_obj,
    car_type_name_en,
    distance_miles,
    pickup_lat=None,
    pickup_lng=None,
    dropoff_lat=None,
    dropoff_lng=None,
    manual_airport_id=None,
    trip_date=None,
):
    """
    Main pricing calculation function with feature flag routing.
    
    Routes to either:
    - Legacy hardcoded pricing (if use_dynamic_pricing=False)
    - New dynamic pricing engine (if use_dynamic_pricing=True)
    
    Args:
        trip_time_obj: datetime.time - Trip time
        car_type_name_en: str - Vehicle type name (must match VehicleType.name_en)
        distance_miles: float - Trip distance in miles
        pickup_lat / pickup_lng / dropoff_lat / dropoff_lng:
            إحداثيات البداية والنهاية لاكتشاف المطار تلقائياً (إن وُجد).
        manual_airport_id: اختيار يدوي لمطار (للتوافق الخلفي مع المنطق السابق في الديناميك).
        trip_date: datetime.date or datetime.datetime - Trip date (for peak time rules when using dynamic pricing).
    
    Returns:
        tuple: (total_cost, regular_vat, airport_vat, base_trip_cost, min_adjustment)
    """
    try:
        from apps.pricing.models import PricingSettings
        from apps.pricing.services.pricing_engine import PricingEngine
        from apps.vehicle.models import VehicleType
        
        settings = PricingSettings.get_settings()
        
        if settings.use_dynamic_pricing:
            try:
                vehicle_type = VehicleType.objects.get(name_en=car_type_name_en)
            except VehicleType.DoesNotExist:
                return _calculate_total_cost_legacy(
                    trip_time_obj,
                    car_type_name_en,
                    distance_miles,
                    pickup_lat=pickup_lat,
                    pickup_lng=pickup_lng,
                    dropoff_lat=dropoff_lat,
                    dropoff_lng=dropoff_lng,
                    trip_date=trip_date,
                )
            
            result = PricingEngine.calculate_trip_cost(
                trip_time=trip_time_obj,
                vehicle_type=vehicle_type,
                distance_miles=distance_miles,
                trip_date=trip_date,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                manual_airport_id=manual_airport_id,
            )
            
            return result.to_tuple()
        else:
            return _calculate_total_cost_legacy(
                trip_time_obj,
                car_type_name_en,
                distance_miles,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                trip_date=trip_date,
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error in dynamic pricing, falling back to legacy: {str(e)}")
        return _calculate_total_cost_legacy(
            trip_time_obj,
            car_type_name_en,
            distance_miles,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            trip_date=trip_date,
        )

