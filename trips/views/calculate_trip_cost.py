from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from apps.vehicle.models import VehicleType
from django.utils.translation import gettext as _ , activate
from ..serializers import TripSerializer 
from utils.common import get_locale , remove_empty_values , is_past_datetime , get_route_with_distance , validate_int_value
from utils.calculate_cost import calculate_total_cost
from utils.utils_trip import prepare_trip_data
from utils.common.error_handlers import (
    create_validation_error_response,
    create_exception_error_response,
    get_bilingual_error_message
)
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

        
class CalculateTripCostView(EMADBaseView):
    http_method_names = ['post']
    permission_classes = [AllowAny]

    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)

        raw_data = remove_empty_values(request.data)
        data = prepare_trip_data(data=raw_data, locale=locale)
        
        serializer = TripSerializer(data=data, context={'request': request, 'locale': locale})
        
        if not serializer.is_valid():
            custom_message = get_bilingual_error_message(
                'Error validating trip data',
                'خطأ في التحقق من بيانات الرحلة',
                locale
            )
            return create_validation_error_response(serializer.errors, locale, custom_message)

        res = get_route_with_distance(
            pickup_lat=data.get('pickup_lat'),
            pickup_lng=data.get('pickup_lng'),
            dropoff_lat=data.get('dropoff_lat'),
            dropoff_lng=data.get('dropoff_lng'),
            stop_points=data.get('stop_points', [])
        )

        distance_miles = res['distance_miles']
        validated_data = serializer.validated_data
        trip_time_obj = validated_data.get('trip_time')
        trip_date = validated_data.get('trip_date')
        passengers_count = validated_data.get('passengers_count')

        car_types_qs = VehicleType.objects.filter(max_passengers_count__gte=passengers_count)

        car_type_list = []
        failed_car_types = []
        distance_too_long = False
        
        for car_type_obj in car_types_qs:
            try:
                total_cost, regular_vat, airport_vat, base_trip_cost, min_adjustment = calculate_total_cost(
                    trip_time_obj,
                    car_type_obj.name_en,
                    distance_miles,
                    pickup_lat=data.get('pickup_lat'),
                    pickup_lng=data.get('pickup_lng'),
                    dropoff_lat=data.get('dropoff_lat'),
                    dropoff_lng=data.get('dropoff_lng'),
                    manual_airport_id=data.get('airport'),
                    trip_date=trip_date,
                )
                # regular_vat = round(regular_vat + min_adjustment, 2)
                car_type_list.append({
                    "id": car_type_obj.id,
                    "name_en": car_type_obj.name_en,
                    "name_ar": car_type_obj.name_ar,
                    "desc_en": car_type_obj.desc_en,
                    "desc_ar": car_type_obj.desc_ar,
                    "icon_url": request.build_absolute_uri(car_type_obj.icon.url) if car_type_obj.icon else None,
                    "max_passengers_count": car_type_obj.max_passengers_count,
                    "total_cost": total_cost,
                    'regular_vat': regular_vat,
                    'airport_vat': airport_vat,
                    'base_trip_cost': base_trip_cost,
                    'min_adjustment': min_adjustment,
                })
            except ValueError as e:
                # Handle "No rate found" error - distance too long or unsupported car type
                error_msg = str(e)
                if "No rate found" in error_msg:
                    # Distance exceeds maximum supported distance (90 miles)
                    distance_too_long = True
                    failed_car_types.append(car_type_obj.name_en)
                else:
                    # Other ValueError (e.g., unsupported car type) - skip this car type
                    failed_car_types.append(car_type_obj.name_en)
                    continue
            except ValidationError as ve:
                # Handle ValidationError from calculate_total_cost (e.g., unsupported car type) - skip this car type
                failed_car_types.append(car_type_obj.name_en)
                continue
        
        # If distance is too long for all car types, return error
        if distance_too_long and len(car_type_list) == 0:
            message = get_bilingual_error_message(
                f"Trip distance ({distance_miles:.1f} miles) exceeds the maximum supported distance (90 miles). Please contact us directly at 07464 940 000 for trips over 90 miles.",
                f"مسافة الرحلة ({distance_miles:.1f} ميل) تتجاوز الحد الأقصى للمسافة المدعومة (90 ميل). يرجى الاتصال بنا مباشرة على 07464 940 000 للرحلات التي تزيد عن 90 ميل.",
                locale
            )
            return create_validation_error_response(
                {'details': message},
                locale,
                get_bilingual_error_message(
                    'Error calculating trip cost',
                    'خطأ في حساب تكلفة الرحلة',
                    locale
                )
            )
        
        # If no car types could be calculated, return error
        if len(car_type_list) == 0:
            if failed_car_types:
                message = get_bilingual_error_message(
                    f"Unable to calculate cost for any available car types. Failed car types: {', '.join(failed_car_types)}",
                    f"تعذر حساب التكلفة لأي من أنواع السيارات المتاحة. أنواع السيارات الفاشلة: {', '.join(failed_car_types)}",
                    locale
                )
            else:
                message = get_bilingual_error_message(
                    "No car types available for the specified number of passengers.",
                    "لا توجد أنواع سيارات متاحة لعدد الركاب المحدد.",
                    locale
                )
            return create_validation_error_response(
                {'details': message},
                locale,
                get_bilingual_error_message(
                    'Error calculating trip cost',
                    'خطأ في حساب تكلفة الرحلة',
                    locale
                )
            )

        return Response({
            "success": True,
            "car_type": car_type_list,
            "route_polyline": res['route_polyline'],
            "distance_miles": distance_miles,
            "expected_trip_duration_minutes": res['duration_minutes'],
            "distance_meters": res['distance_meters'],
        }, status=status.HTTP_200_OK)
