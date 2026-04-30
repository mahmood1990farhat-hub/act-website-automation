from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
import stripe
from django.conf import settings
from apps.trips.models import Trip, StopPoint, Airport
from apps.payments.models import PendingPayment
from apps.passengers.models import Passenger
from apps.vehicle.models import VehicleType
from utils.common.notifications import (
    notify_all_drivers,
    NOTIFICATION_TYPE_TRIP_CREATED,
    NOTIFICATION_TYPE_NEW_TRIP_REQUEST
)
from utils.common import notify_user
from utils.common.email import send_passenger_confirmation, send_internal_notification
from utils.common.google_map import reverse_geocode
from utils.common import get_route_with_distance
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error(f"[STRIPE WEBHOOK] Invalid webhook: {str(e)}")
        return HttpResponse(status=400)

    event_type = event.get('type')

    if event_type == 'payment_intent.succeeded':
        handle_payment_succeeded(event)

    elif event_type == 'payment_intent.payment_failed':
        handle_payment_failed(event)

    return HttpResponse(status=200)


def handle_payment_succeeded(event):
    payment_intent = event['data']['object']
    payment_intent_id = payment_intent['id']
    metadata = payment_intent.get('metadata') or {}
    pending_payment_id = metadata.get('pending_payment_id')

    logger.info(f"[WEBHOOK] Processing success for PI={payment_intent_id}")

    try:
        with transaction.atomic():
            trip = create_trip_from_payment(payment_intent, pending_payment_id)

        post_trip_creation(trip)

    except Exception as e:
        logger.error(f"[WEBHOOK] Failed for PI={payment_intent_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def handle_payment_failed(event):
    payment_intent = event['data']['object']
    payment_intent_id = payment_intent['id']

    logger.info(f"[WEBHOOK] Payment failed for PI={payment_intent_id}")


def create_trip_from_payment(payment_intent, pending_payment_id):
    payment_intent_id = payment_intent['id']
    existing_trip = Trip.objects.filter(
        stripe_payment_intent=payment_intent_id
    ).first()

    if existing_trip:
        logger.info(f"[WEBHOOK] Trip already exists: {existing_trip.id}")
        return existing_trip

    pending_payment = get_pending_payment(payment_intent_id, pending_payment_id)
    if not pending_payment:
        raise Exception(f"PendingPayment not found for PI={payment_intent_id}")

    passenger = Passenger.objects.get(id=pending_payment.passenger_id)

    trip_data = normalize_trip_data(pending_payment.trip_data)
    price = pending_payment.price_breakdown
    card_details = extract_card_details(payment_intent)

    car_type = VehicleType.objects.get(id=int(trip_data['car_type']))

    airport = None
    if trip_data.get('airport'):
        airport = Airport.objects.filter(id=trip_data['airport']).first()

    route_data = calculate_route_safe(trip_data)

    trip = Trip.objects.create(
        passenger=passenger,
        car_type=car_type,
        airport=airport,
        stripe_payment_intent=payment_intent_id,
        is_paid=True,
        status='pending',

        pickup_lat=trip_data['pickup_lat'],
        pickup_lng=trip_data['pickup_lng'],
        dropoff_lat=trip_data['dropoff_lat'],
        dropoff_lng=trip_data['dropoff_lng'],
        trip_date=trip_data['trip_date'],
        trip_time=trip_data['trip_time'],

        passengers_count=trip_data.get('passengers_count', 1),
        large_suitcase=trip_data.get('large_suitcase', 0),
        small_suitcase=trip_data.get('small_suitcase', 0),

        pickup_place_id=trip_data.get('pickup_place_id'),
        dropoff_place_id=trip_data.get('dropoff_place_id'),
        pickup_postal_code=trip_data.get('pickup_postal_code'),
        dropoff_postal_code=trip_data.get('dropoff_postal_code'),
        airport_direction=trip_data.get('airport_direction'),

        route_polyline=route_data.get('route_polyline', ''),
        distance_miles=route_data.get('distance_miles', 0),
        expected_trip_duration_minutes=route_data.get('expected_trip_duration_minutes', 0),

        cost=price['total_cost'],
        base_trip_cost=price['base_trip_cost'],
        regular_vat=price['regular_vat'],
        airport_vat=price['airport_vat'],
        min_adjustment=price['min_adjustment'],
        last4=card_details.get('last4'),
        card_brand=card_details.get('card_brand'),
    )

    create_stop_points(trip, trip_data.get('stop_points', []))

    pending_payment.delete()
    logger.info(f"[WEBHOOK] Trip created: {trip.id}")

    return trip


def extract_card_details(payment_intent):
    charges = ((payment_intent.get('charges') or {}).get('data') or [])
    card = {}

    if charges:
        first_charge = charges[0] or {}
        card = ((first_charge.get('payment_method_details') or {}).get('card') or {})

    # Fallback in case webhook payload structure differs and latest_charge is expanded.
    if not card:
        latest_charge = payment_intent.get('latest_charge')
        if isinstance(latest_charge, dict):
            card = ((latest_charge.get('payment_method_details') or {}).get('card') or {})

    return {
        'last4': card.get('last4'),
        'card_brand': card.get('brand'),
    }


def get_pending_payment(payment_intent_id, pending_payment_id):
    if pending_payment_id:
        return PendingPayment.objects.filter(id=pending_payment_id).first()

    return PendingPayment.objects.filter(
        payment_intent_id=payment_intent_id
    ).first()


def normalize_trip_data(data):
    data = data.copy()

    if isinstance(data.get('trip_date'), str):
        data['trip_date'] = datetime.strptime(data['trip_date'], '%Y-%m-%d').date()

    if isinstance(data.get('trip_time'), str):
        from django.utils.dateparse import parse_time
        data['trip_time'] = parse_time(data['trip_time'])

    return data


def calculate_route_safe(trip_data):
    try:
        result = get_route_with_distance(
            pickup_lat=trip_data['pickup_lat'],
            pickup_lng=trip_data['pickup_lng'],
            dropoff_lat=trip_data['dropoff_lat'],
            dropoff_lng=trip_data['dropoff_lng'],
            stop_points=trip_data.get('stop_points', [])
        )

        return {
            "route_polyline": result.get('route_polyline', ''),
            "distance_miles": result.get('distance_miles', 0),
            "expected_trip_duration_minutes": result.get('duration_minutes', 0)
        }
    except Exception as e:
        logger.warning(f"[WEBHOOK] Route calc failed: {str(e)}")
        return {}


def create_stop_points(trip, stop_points):
    for sp in stop_points:
        StopPoint.objects.create(
            trip=trip,
            point_lat=sp.get('point_lat'),
            point_lng=sp.get('point_lng'),
            point_place_id=sp.get('point_place_id'),
            point_postal_code=sp.get('point_postal_code'),
            point_str=sp.get('point_str')
        )


def post_trip_creation(trip):
    try:
        enrich_addresses(trip)
        send_notifications(trip)
    except Exception as e:
        logger.error(f"[WEBHOOK] Post processing failed for trip {trip.id}: {str(e)}")


def enrich_addresses(trip):
    try:
        pickup_geo = reverse_geocode(trip.pickup_lat, trip.pickup_lng)
        dropoff_geo = reverse_geocode(trip.dropoff_lat, trip.dropoff_lng)

        trip.pickup_str = (pickup_geo or {}).get("formatted_address") or f"{trip.pickup_lat},{trip.pickup_lng}"
        trip.dropoff_str = (dropoff_geo or {}).get("formatted_address") or f"{trip.dropoff_lat},{trip.dropoff_lng}"

        trip.save(update_fields=["pickup_str", "dropoff_str"])
    except Exception as e:
        logger.warning(f"[WEBHOOK] Reverse geocode failed: {str(e)}")


def send_notifications(trip):
    try:
        passenger = trip.passenger

        if passenger and passenger.user:
            send_passenger_confirmation(passenger.user, trip)

            notify_user(
                user=passenger.user.id,
                title_en='Trip Created',
                title_ar='تم إنشاء الرحلة',
                desc_en=f'Your trip #{trip.id} has been created successfully.',
                desc_ar=f'تم إنشاء رحلتك #{trip.id} بنجاح.',
                locale='en',
                notification_type=NOTIFICATION_TYPE_TRIP_CREATED,
                trip_id=trip.id
            )

        send_internal_notification(trip)

        notify_all_drivers(
            title_en='New Trip Available',
            title_ar='رحلة جديدة متاحة',
            desc_en=f'A new trip #{trip.id} is available.',
            desc_ar=f'رحلة جديدة #{trip.id} متاحة.',
            locale='en',
            trip_id=trip.id,
            notification_type=NOTIFICATION_TYPE_NEW_TRIP_REQUEST
        )

    except Exception as e:
        logger.error(f"[WEBHOOK] Notification failed: {str(e)}")

