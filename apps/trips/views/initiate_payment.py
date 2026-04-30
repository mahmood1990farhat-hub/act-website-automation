from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger, IsVerifiedAndProfileCompleted
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from datetime import timedelta
from utils.common import get_locale, remove_empty_values, get_route_with_distance
from utils.utils_trip import prepare_trip_data
from utils.calculate_cost import calculate_total_cost
from apps.payments.models import PendingPayment
from apps.vehicle.models import VehicleType
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class InitiatePaymentView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['post']

    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)

        raw_data = remove_empty_values(request.data)
        data = prepare_trip_data(data=raw_data, locale=locale)

        car_type_id = data.get('car_type')
        if not car_type_id:
            raise ValidationError({'car_type': _('Car type is required')})

        try:
            car_type = VehicleType.objects.get(id=car_type_id)
        except VehicleType.DoesNotExist:
            raise ValidationError({'car_type': _('Invalid car type')})

        res = get_route_with_distance(
            pickup_lat=data.get('pickup_lat'),
            pickup_lng=data.get('pickup_lng'),
            dropoff_lat=data.get('dropoff_lat'),
            dropoff_lng=data.get('dropoff_lng'),
            stop_points=data.get('stop_points', [])
        )
        distance_miles = res['distance_miles']

        trip_time_obj = data.get('trip_time')
        if isinstance(trip_time_obj, str):
            from django.utils.dateparse import parse_time
            trip_time_obj = parse_time(trip_time_obj)

        trip_date = data.get('trip_date')
        if isinstance(trip_date, str):
            from django.utils.dateparse import parse_date
            trip_date = parse_date(trip_date)

        total_cost, regular_vat, airport_vat, base_trip_cost, min_adjustment = calculate_total_cost(
            trip_time_obj,
            car_type.name_en,
            distance_miles,
            pickup_lat=data.get('pickup_lat'),
            pickup_lng=data.get('pickup_lng'),
            dropoff_lat=data.get('dropoff_lat'),
            dropoff_lng=data.get('dropoff_lng'),
            manual_airport_id=data.get('airport'),
            trip_date=trip_date,
        )

        price_breakdown = {
            'total_cost': float(total_cost),
            'base_trip_cost': float(base_trip_cost),
            'regular_vat': float(regular_vat),
            'airport_vat': float(airport_vat),
            'min_adjustment': float(min_adjustment),
        }

        if not total_cost or total_cost <= 0:
            raise ValidationError({'cost': _('Invalid trip cost. Please contact support.')})

        amount_in_cents = int(float(total_cost) * 100)
        if amount_in_cents <= 0:
            raise ValidationError({'amount': _('Payment amount is invalid or zero')})

        trip_data_for_storage = data.copy()
        trip_data_for_storage['distance_miles'] = distance_miles
        trip_data_for_storage['expected_trip_duration_minutes'] = res.get('duration_minutes', 0)
        trip_data_for_storage['route_polyline'] = res.get('route_polyline', '')

        if 'stop_points' in raw_data:
            trip_data_for_storage['stop_points'] = raw_data.get('stop_points', [])

        if 'trip_time' in trip_data_for_storage and hasattr(trip_data_for_storage['trip_time'], 'strftime'):
            trip_data_for_storage['trip_time'] = trip_data_for_storage['trip_time'].strftime('%H:%M:%S')
        if 'trip_date' in trip_data_for_storage and hasattr(trip_data_for_storage['trip_date'], 'strftime'):
            trip_data_for_storage['trip_date'] = trip_data_for_storage['trip_date'].strftime('%Y-%m-%d')

        if trip_data_for_storage.get('airport') and hasattr(trip_data_for_storage['airport'], 'id'):
            trip_data_for_storage['airport'] = trip_data_for_storage['airport'].id

        trip_data_for_storage['car_type'] = car_type.id

        pending_payment = PendingPayment.objects.create(
            payment_intent_id=None,
            price_breakdown=price_breakdown,
            trip_data=trip_data_for_storage,
            passenger_id=request.user.passenger_profile.id,
            currency='GBP',
            expires_at=timezone.now() + timedelta(minutes=15)
        )

        idempotency_key = f"payment_{pending_payment.id}"
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="gbp",
            metadata={
                "pending_payment_id": str(pending_payment.id),
                "passenger_id": str(request.user.passenger_profile.id),
                "car_type_id": str(car_type.id),
            },
            idempotency_key=idempotency_key
        )

        pending_payment.payment_intent_id = payment_intent.id
        pending_payment.save(update_fields=["payment_intent_id"])

        logger.info(
            f"Payment initiated for passenger {request.user.passenger_profile.id}: "
            f"PaymentIntent {payment_intent.id}, amount: {total_cost}"
        )

        return Response({
            "success": True,
            "message": _("Payment initiated successfully"),
            "client_secret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id,
            "pending_payment_id": pending_payment.id,
        }, status=status.HTTP_200_OK)




