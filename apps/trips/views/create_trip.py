from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger , IsVerifiedAndProfileCompleted
from django.utils.translation import gettext as _ , activate
from ..serializers import TripSerializer 
from utils.common import get_locale , remove_empty_values, notify_user
from utils.common.notifications import notify_all_drivers, NOTIFICATION_TYPE_TRIP_CREATED, NOTIFICATION_TYPE_NEW_TRIP_REQUEST 
from utils.utils_trip import prepare_trip_data
from utils.common.error_handlers import (
    create_validation_error_response,
    create_exception_error_response,
    create_error_response,
    get_bilingual_error_message
)
import stripe
from django.conf import settings
from utils.common.email import send_passenger_confirmation, send_internal_notification
from utils.common.google_map import reverse_geocode
import logging
import traceback

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY



class CreateTripView(EMADBaseView):
    """
    Deprecated: Passengers must use payment-first flow.
    POST /api/trips/initiate-payment/ to book; trip is created only after successful payment.
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['post']

    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        message = get_bilingual_error_message(
            'Booking requires payment first. Use the initiate-payment endpoint to book a trip.',
            'الحجز يتطلب الدفع أولاً. استخدم نقطة بدء الدفع لحجز رحلة.',
            locale
        )
        return create_error_response(
            message,
            locale=locale,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def _handle_post_legacy(self, request):
        """Legacy implementation - do not use. Kept for reference."""
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            raw_data = remove_empty_values(request.data)
            data = prepare_trip_data(data=raw_data, locale=locale)
        
        except ValidationError as e:
            # Handle validation errors from prepare_trip_data
            if isinstance(e.detail, dict):
                return create_validation_error_response(e.detail, locale)
            else:
                errors = {'detail': e.detail} if not isinstance(e.detail, dict) else e.detail
                return create_validation_error_response(errors, locale)
        
        except Exception as e:
            # Log unexpected errors in prepare_trip_data
            logger.error(f"Error in prepare_trip_data: {str(e)}")
            logger.error(traceback.format_exc())
            custom_message = get_bilingual_error_message(
                'Error processing trip location data',
                'خطأ في معالجة بيانات موقع الرحلة',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        try:
            serializer = TripSerializer(data=data, context={'request': request, 'locale': locale})
            if not serializer.is_valid():
                custom_message = get_bilingual_error_message(
                    'Error validating trip data',
                    'خطأ في التحقق من بيانات الرحلة',
                    locale
                )
                return create_validation_error_response(serializer.errors, locale, custom_message)
            
            trip = serializer.save()
        except ValidationError as e:
            # Handle ValidationError from serializer
            if isinstance(e.detail, dict):
                return create_validation_error_response(e.detail, locale)
            else:
                errors = {'detail': e.detail} if not isinstance(e.detail, dict) else e.detail
                return create_validation_error_response(errors, locale)
        
        except Exception as e:
            # Log unexpected errors in serializer
            logger.error(f"Error in TripSerializer: {str(e)}")
            logger.error(traceback.format_exc())
            custom_message = get_bilingual_error_message(
                'Error creating trip',
                'خطأ في إنشاء الرحلة',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        try:
            # Reverse geocode addresses
            pickup_geo = reverse_geocode(trip.pickup_lat, trip.pickup_lng)
            dropoff_geo = reverse_geocode(trip.dropoff_lat, trip.dropoff_lng)

            trip.pickup_str = (pickup_geo or {}).get("formatted_address") or f"{trip.pickup_lat},{trip.pickup_lng}"
            trip.dropoff_str = (dropoff_geo or {}).get("formatted_address") or f"{trip.dropoff_lat},{trip.dropoff_lng}"
            trip.save(update_fields=["pickup_str", "dropoff_str"])
      
        except Exception as e:
            # Log but don't fail - addresses are optional
            logger.warning(f"Error reverse geocoding addresses: {str(e)}")
            # Continue without formatted addresses
        
        try:
            cost = trip.cost
            if not cost or cost <= 0:
                raise ValueError("Trip cost is invalid or zero")
            
            amount_in_cents = int(float(cost) * 100)
            if amount_in_cents <= 0:
                raise ValueError("Payment amount is invalid or zero")
        
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating payment amount: {str(e)}")
            logger.error(traceback.format_exc())
            custom_message = get_bilingual_error_message(
                'Error calculating trip cost. Please contact support.',
                'خطأ في حساب تكلفة الرحلة. يرجى الاتصال بالدعم.',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency="gbp",
                metadata={"trip_id": trip.id}
            )
            trip.stripe_payment_intent = payment_intent.id
            trip.save(update_fields=['stripe_payment_intent'])
        except stripe.error.StripeError as e:
            # Handle Stripe-specific errors
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            logger.error(traceback.format_exc())
            custom_message = get_bilingual_error_message(
                'Payment processing error. Please try again or contact support.',
                'خطأ في معالجة الدفع. يرجى المحاولة مرة أخرى أو الاتصال بالدعم.',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            logger.error(traceback.format_exc())
            custom_message = get_bilingual_error_message(
                'Error processing payment. Please try again.',
                'خطأ في معالجة الدفع. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        try:
            # Send emails (non-blocking, failures are logged but don't fail the request)
            print(f"[TRIP CREATION] ⚠️ Attempting to send emails for trip #{trip.id}")
            logger.info(f"[TRIP CREATION] Attempting to send emails for trip #{trip.id}")
            print(f"[TRIP CREATION] ⚠️ User: {request.user.id}, Email: {request.user.email}")
            logger.info(f"[TRIP CREATION] User: {request.user.id}, Email: {request.user.email}")
            print(f"[TRIP CREATION] ⚠️ Calling send_passenger_confirmation...")
            logger.info(f"[TRIP CREATION] Calling send_passenger_confirmation...")
            send_passenger_confirmation(request.user, trip)
            print(f"[TRIP CREATION] ⚠️ Called send_passenger_confirmation, now calling send_internal_notification...")
            logger.info(f"[TRIP CREATION] Called send_passenger_confirmation, now calling send_internal_notification...")
            send_internal_notification(trip)
            print(f"[TRIP CREATION] ⚠️ Email sending initiated for trip #{trip.id}")
            logger.info(f"[TRIP CREATION] Email sending initiated for trip #{trip.id} (check logs for delivery status)")
        except Exception as e:
            # Log but don't fail - emails are optional
            print(f"[TRIP CREATION] ❌ ERROR: {str(e)}")
            logger.error(f"[TRIP CREATION] ❌ Error initiating email sending for trip #{trip.id}: {str(e)}")
            logger.error(f"[TRIP CREATION] Error type: {type(e).__name__}")
            logger.error(traceback.format_exc())

        # Send notification to passenger about trip creation
        # Uses smart fallback: tries async (Celery) first, falls back to sync if Redis unavailable
        try:
            logger.info(f"Attempting to send trip creation notification for trip {trip.id} to user {request.user.id}")
            success = notify_user(
                user=request.user.id,
                title_en='Trip Created',
                title_ar='تم إنشاء الرحلة',
                desc_en=f'Your trip #{trip.id} has been created successfully. Waiting for driver assignment...',
                desc_ar=f'تم إنشاء رحلتك #{trip.id} بنجاح. في انتظار تعيين السائق...',
                locale=locale,
                notification_type=NOTIFICATION_TYPE_TRIP_CREATED,
                trip_id=trip.id
            )
            if success:
                logger.info(f"Notification sent successfully for trip {trip.id} (async or sync)")
            else:
                logger.warning(f"Notification failed for trip {trip.id}, but continuing...")
        except Exception as e:
            # Log but don't fail - notifications are optional
            logger.error(f"Failed to send notification for trip {trip.id}: {str(e)}")
            logger.error(traceback.format_exc())

        # Notify all active drivers about the new trip request
        try:
            logger.info(f"Attempting to notify all drivers about new trip {trip.id}")
            driver_notification_result = notify_all_drivers(
                title_en='New Trip Available',
                title_ar='رحلة جديدة متاحة',
                desc_en=f'A new trip request #{trip.id} is available. Check the app to accept it.',
                desc_ar=f'طلب رحلة جديد #{trip.id} متاح. تحقق من التطبيق لقبوله.',
                locale=locale,
                trip_id=trip.id,
                notification_type=NOTIFICATION_TYPE_NEW_TRIP_REQUEST
            )
            logger.info(f"Driver notifications result for trip {trip.id}: {driver_notification_result}")
        except Exception as e:
            # Log but don't fail - notifications are optional
            logger.error(f"Failed to notify drivers about trip {trip.id}: {str(e)}")
            logger.error(traceback.format_exc())

        return Response({
            "message": _("Your trip booked successfully"),
            "trip_id": trip.id,
            "client_secret": payment_intent.client_secret
        }, status=status.HTTP_200_OK)



