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
from apps.trips.services.booking_confirmation import ensure_booking_confirmation_pdf
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
    payment_intent = (event.get('data') or {}).get('object') or {}
    payment_intent_id = payment_intent.get('id')
    pending_payment_id = (payment_intent.get('metadata') or {}).get('pending_payment_id')

    logger.info(
        f"[STRIPE WEBHOOK] Received event_type={event_type}, "
        f"payment_intent_id={payment_intent_id}, pending_payment_id={pending_payment_id}"
    )

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
        logger.info(
            f"[WEBHOOK] Creating trip for PI={payment_intent_id}, pending_payment_id={pending_payment_id}"
        )
        with transaction.atomic():
            trip = create_trip_from_payment(payment_intent, pending_payment_id)

        logger.info(
            f"[WEBHOOK] Trip create/lookup complete for PI={payment_intent_id}: "
            f"trip_id={trip.id}, passenger_email={trip.passenger_email}, "
            f"is_guest_checkout={trip.is_guest_checkout}"
        )

        try:
            logger.info(f"[WEBHOOK] Enriching addresses before PDF generation for trip {trip.id}")
            enrich_addresses(trip)
            logger.info(f"[WEBHOOK] Address enrichment complete before PDF generation for trip {trip.id}")
        except Exception as address_error:
            logger.warning(
                f"[WEBHOOK] Failed to enrich addresses before PDF generation for trip {trip.id}: {str(address_error)}",
                exc_info=True,
            )

        try:
            logger.info(f"[WEBHOOK] Generating booking confirmation PDF for trip {trip.id}")
            ensure_booking_confirmation_pdf(trip)
            logger.info(f"[WEBHOOK] Booking confirmation PDF ready for trip {trip.id}")
        except Exception as pdf_error:
            logger.warning(
                f"[WEBHOOK] Failed to generate booking confirmation PDF for trip {trip.id}: {str(pdf_error)}",
                exc_info=True,
            )

        logger.info(f"[WEBHOOK] Starting post_trip_creation for trip {trip.id}")
        post_trip_creation(trip)
        logger.info(f"[WEBHOOK] Finished post_trip_creation for trip {trip.id}")

    except Exception as e:
        logger.exception(f"[WEBHOOK] Failed for PI={payment_intent_id}: {str(e)}")


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

    if pending_payment.passenger_id:
        passenger = Passenger.objects.get(id=pending_payment.passenger_id)
        is_guest_checkout = False
    else:
        passenger = None
        is_guest_checkout = True

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
        passenger_name=pending_payment.passenger_name,
        passenger_email=pending_payment.passenger_email,
        passenger_country_code=pending_payment.passenger_country_code,
        passenger_phone=pending_payment.passenger_phone,
        booking_details=pending_payment.booking_details or {},
        is_guest_checkout=is_guest_checkout,
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
    payment_method_details = {}

    if charges:
        first_charge = charges[0] or {}
        payment_method_details = first_charge.get('payment_method_details') or {}

    # Fallback in case webhook payload structure differs and latest_charge is expanded.
    if not payment_method_details:
        latest_charge = payment_intent.get('latest_charge')
        if isinstance(latest_charge, dict):
            payment_method_details = latest_charge.get('payment_method_details') or {}
        elif isinstance(latest_charge, str) and latest_charge:
            try:
                charge = stripe.Charge.retrieve(latest_charge)
                payment_method_details = charge.get('payment_method_details') or {}
            except Exception as charge_error:
                logger.warning(
                    f"[WEBHOOK] Unable to retrieve Stripe charge payment details "
                    f"for charge={latest_charge}: {str(charge_error)}",
                    exc_info=True,
                )

    payment_method_type = payment_method_details.get('type')

    if payment_method_type == 'afterpay_clearpay':
        return {
            'last4': None,
            'card_brand': 'Clearpay',
            'payment_method_type': payment_method_type,
        }

    card = payment_method_details.get('card') or {}
    return {
        'last4': card.get('last4'),
        'card_brand': card.get('brand'),
        'payment_method_type': payment_method_type or 'card',
    }


def get_pending_payment(payment_intent_id, pending_payment_id):
    if pending_payment_id:
        pending_payment = PendingPayment.objects.filter(id=pending_payment_id).first()
        if pending_payment:
            logger.info(
                f"[WEBHOOK] PendingPayment lookup by id succeeded: "
                f"pending_payment_id={pending_payment_id}, payment_intent_id={payment_intent_id}"
            )
            return pending_payment

        logger.warning(
            f"[WEBHOOK] PendingPayment lookup by id failed: "
            f"pending_payment_id={pending_payment_id}, payment_intent_id={payment_intent_id}; "
            "falling back to payment_intent_id lookup"
        )

    pending_payment = PendingPayment.objects.filter(
        payment_intent_id=payment_intent_id
    ).first()
    if pending_payment:
        logger.info(
            f"[WEBHOOK] PendingPayment lookup by payment_intent_id succeeded: "
            f"pending_payment_id={pending_payment.id}, payment_intent_id={payment_intent_id}"
        )
    else:
        logger.warning(
            f"[WEBHOOK] PendingPayment lookup by payment_intent_id failed: "
            f"payment_intent_id={payment_intent_id}"
        )

    return pending_payment


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
        logger.info(f"[WEBHOOK] Enriching addresses for trip {trip.id}")
        enrich_addresses(trip)
        logger.info(f"[WEBHOOK] Sending notifications for trip {trip.id}")
        send_notifications(trip)
    except Exception as e:
        logger.exception(f"[WEBHOOK] Post processing failed for trip {trip.id}: {str(e)}")


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
        passenger_user = passenger.user if passenger and passenger.user else None

        passenger_confirmation_sent = send_passenger_confirmation(passenger_user, trip)
        logger.info(
            f"[WEBHOOK] send_passenger_confirmation returned {passenger_confirmation_sent} "
            f"for trip {trip.id}"
        )
        if passenger_user:
            notify_user(
                user=passenger_user.id,
                title_en='Trip Created',
                title_ar='تم إنشاء الرحلة',
                desc_en=f'Your trip #{trip.id} has been created successfully.',
                desc_ar=f'تم إنشاء رحلتك #{trip.id} بنجاح.',
                locale='en',
                notification_type=NOTIFICATION_TYPE_TRIP_CREATED,
                trip_id=trip.id
            )

        internal_notification_sent = send_internal_notification(trip)
        logger.info(
            f"[WEBHOOK] send_internal_notification returned {internal_notification_sent} "
            f"for trip {trip.id}"
        )

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
        logger.exception(f"[WEBHOOK] Notification failed: {str(e)}")

