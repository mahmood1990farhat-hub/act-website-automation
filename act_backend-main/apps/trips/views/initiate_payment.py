from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger, IsVerifiedAndProfileCompleted
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from datetime import timedelta
from utils.common import get_locale, remove_empty_values, get_route_with_distance
from utils.utils_trip import prepare_trip_data
from utils.calculate_cost import calculate_total_cost
from apps.pricing.services.extra_service_resolver import (
    apply_meet_and_greet_pricing,
    persist_authoritative_meet_and_greet,
)
from apps.payments.models import PendingPayment
from apps.vehicle.models import VehicleType
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_authoritative_payment_price(data, car_type, distance_miles, booking_details):
    trip_time = data.get('trip_time')
    if isinstance(trip_time, str):
        trip_time = parse_time(trip_time)

    trip_date = data.get('trip_date')
    if isinstance(trip_date, str):
        trip_date = parse_date(trip_date)

    total_cost, regular_vat, airport_vat, base_trip_cost, min_adjustment = calculate_total_cost(
        trip_time,
        car_type.name_en,
        distance_miles,
        pickup_lat=data.get('pickup_lat'),
        pickup_lng=data.get('pickup_lng'),
        dropoff_lat=data.get('dropoff_lat'),
        dropoff_lng=data.get('dropoff_lng'),
        manual_airport_id=data.get('airport'),
        trip_date=trip_date,
    )
    extra_pricing = apply_meet_and_greet_pricing(
        total_cost=total_cost,
        booking_details=booking_details,
        vehicle_type=car_type,
        pickup_lat=data.get('pickup_lat'),
        pickup_lng=data.get('pickup_lng'),
        dropoff_lat=data.get('dropoff_lat'),
        dropoff_lng=data.get('dropoff_lng'),
        manual_airport_id=data.get('airport'),
    )
    authoritative_details = persist_authoritative_meet_and_greet(
        booking_details,
        extra_pricing,
    )
    price_breakdown = {
        'total_cost': float(extra_pricing['total_cost']),
        'base_trip_cost': float(base_trip_cost),
        'regular_vat': float(regular_vat),
        'airport_vat': float(airport_vat),
        'min_adjustment': float(min_adjustment),
        'meet_and_greet_fee': float(extra_pricing['meet_and_greet_fee']),
        'meet_and_greet_total': float(extra_pricing['meet_and_greet_total']),
    }
    return (
        extra_pricing['total_cost'],
        price_breakdown,
        authoritative_details,
        trip_time,
        trip_date,
    )


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

        booking_details = request.data.get('booking_details') or {}
        total_cost, price_breakdown, booking_details, trip_time_obj, trip_date = (
            calculate_authoritative_payment_price(
                data,
                car_type,
                distance_miles,
                booking_details,
            )
        )

        meet_and_greet_total = price_breakdown['meet_and_greet_total']

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
            passenger_name=request.data.get('passenger_name') or '',
            passenger_email=request.data.get('passenger_email') or '',
            passenger_country_code=request.data.get('passenger_country_code') or '',
            passenger_phone=request.data.get('passenger_phone') or '',
            booking_details=booking_details,
            currency='GBP',
            expires_at=timezone.now() + timedelta(minutes=15)
        )

        idempotency_key = f"payment_{pending_payment.id}"
        def stripe_metadata_value(value, max_length=500):
            if value is None:
                return ""
            return str(value)[:max_length]

        passenger_name = " ".join(
            part for part in [request.user.first_name, request.user.last_name] if part
        ).strip()
        payment_metadata = {
            "pending_payment_id": stripe_metadata_value(pending_payment.id),
            "passenger_id": stripe_metadata_value(request.user.passenger_profile.id),
            "passenger_email": stripe_metadata_value(request.user.email),
            "passenger_name": stripe_metadata_value(passenger_name),
            "car_type_id": stripe_metadata_value(car_type.id),
            "car_type": stripe_metadata_value(car_type.name_en),
            "trip_date": stripe_metadata_value(trip_date),
            "trip_time": stripe_metadata_value(trip_time_obj),
            "passengers_count": stripe_metadata_value(data.get("passengers_count")),
            "meet_and_greet_total": stripe_metadata_value(meet_and_greet_total),
            "currency": "GBP",
        }
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="gbp",
            metadata=payment_metadata,
            idempotency_key=idempotency_key
        )

        booking_reference = f"ACT-{payment_intent.id}"
        stripe.PaymentIntent.modify(
            payment_intent.id,
            description=f"ACT booking {booking_reference}",
            metadata={
                **payment_metadata,
                "act_booking_reference": booking_reference,
                "act_invoice_number": booking_reference,
            },
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
            "price_breakdown": price_breakdown,
        }, status=status.HTTP_200_OK)


class InitiateGuestPaymentView(EMADBaseView):
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def _clean_required_text(self, raw_value, field_name, max_length):
        value = str(raw_value or '').strip()
        if not value:
            raise ValidationError({field_name: _(f'{field_name} is required')})
        if len(value) > max_length:
            raise ValidationError({
                field_name: _(f'{field_name} must be {max_length} characters or fewer')
            })
        return value

    def _validate_guest_contact(self, request):
        passenger_name = self._clean_required_text(
            request.data.get('passenger_name'),
            'passenger_name',
            255,
        )
        passenger_email = self._clean_required_text(
            request.data.get('passenger_email'),
            'passenger_email',
            254,
        )
        passenger_country_code = self._clean_required_text(
            request.data.get('passenger_country_code'),
            'passenger_country_code',
            64,
        )
        passenger_phone = self._clean_required_text(
            request.data.get('passenger_phone'),
            'passenger_phone',
            32,
        )

        try:
            validate_email(passenger_email)
        except DjangoValidationError:
            raise ValidationError({'passenger_email': _('Enter a valid email address')})

        return {
            'passenger_name': passenger_name,
            'passenger_email': passenger_email,
            'passenger_country_code': passenger_country_code,
            'passenger_phone': passenger_phone,
        }

    def _stripe_metadata_value(self, value, max_length=500):
        if value is None:
            return ""
        return str(value)[:max_length]

    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)

        guest_contact = self._validate_guest_contact(request)

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

        booking_details = request.data.get('booking_details') or {}
        total_cost, price_breakdown, booking_details, trip_time_obj, trip_date = (
            calculate_authoritative_payment_price(
                data,
                car_type,
                distance_miles,
                booking_details,
            )
        )
        meet_and_greet_total = price_breakdown['meet_and_greet_total']

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
            passenger_id=None,
            passenger_name=guest_contact['passenger_name'],
            passenger_email=guest_contact['passenger_email'],
            passenger_country_code=guest_contact['passenger_country_code'],
            passenger_phone=guest_contact['passenger_phone'],
            booking_details=booking_details,
            currency='GBP',
            expires_at=timezone.now() + timedelta(minutes=15)
        )

        idempotency_key = f"guest_payment_{pending_payment.id}"
        payment_metadata = {
            "pending_payment_id": self._stripe_metadata_value(pending_payment.id),
            "passenger_id": "guest",
            "passenger_email": self._stripe_metadata_value(guest_contact['passenger_email']),
            "passenger_name": self._stripe_metadata_value(guest_contact['passenger_name']),
            "car_type_id": self._stripe_metadata_value(car_type.id),
            "car_type": self._stripe_metadata_value(car_type.name_en),
            "trip_date": self._stripe_metadata_value(trip_date),
            "trip_time": self._stripe_metadata_value(trip_time_obj),
            "passengers_count": self._stripe_metadata_value(data.get("passengers_count")),
            "meet_and_greet_total": self._stripe_metadata_value(meet_and_greet_total),
            "currency": "GBP",
        }
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="gbp",
            metadata=payment_metadata,
            receipt_email=guest_contact['passenger_email'],
            idempotency_key=idempotency_key
        )

        booking_reference = f"ACT-{payment_intent.id}"
        stripe.PaymentIntent.modify(
            payment_intent.id,
            description=f"ACT booking {booking_reference}",
            metadata={
                **payment_metadata,
                "act_booking_reference": booking_reference,
                "act_invoice_number": booking_reference,
            },
        )

        pending_payment.payment_intent_id = payment_intent.id
        pending_payment.save(update_fields=["payment_intent_id"])

        logger.info(
            f"Guest payment initiated: PaymentIntent {payment_intent.id}, "
            f"PendingPayment {pending_payment.id}, amount: {total_cost}"
        )

        return Response({
            "success": True,
            "message": _("Payment initiated successfully"),
            "client_secret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id,
            "pending_payment_id": pending_payment.id,
            "price_breakdown": price_breakdown,
        }, status=status.HTTP_200_OK)




