from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger, IsVerifiedAndProfileCompleted
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404
from utils.common import get_locale, paginate_queryset
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    get_bilingual_error_message
)
from ..models import Trip
from ..serializers import TripWithStopPointSerializer
from apps.passengers.models import Passenger
import stripe
from django.conf import settings
from utils.common.email import (
    send_passenger_trip_cancellation_to_passenger,
    send_passenger_trip_cancellation_to_admin,
)
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class PassengerTripsListView(EMADBaseView):
    """
    List all passenger trips with pagination and status filtering
    GET /api/passenger/trips/
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['get']

    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            passenger = user.passenger_profile
        except Passenger.DoesNotExist:
            message = get_bilingual_error_message(
                'Passenger profile not found.',
                'ملف الراكب غير موجود.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        # Get status filter from query params
        trip_status_param = request.query_params.get('status', '').strip()
        
        # Build queryset
        queryset = Trip.objects.filter(
            passenger=passenger
        ).select_related(
            'base_driver__user',
            'base_driver__normal_driver__vehicle',
            'car_type',
            'airport'
        ).prefetch_related('stop_points').order_by('-created_at')

        # Apply status filter if provided
        if trip_status_param:
            trip_statuses = [s.strip() for s in trip_status_param.split(',')]
            allowed_statuses = ['pending', 'accepted', 'driver_on_the_way', 'active', 'completed', 'cancelled']
            
            invalid_statuses = [s for s in trip_statuses if s not in allowed_statuses]
            if invalid_statuses:
                message = get_bilingual_error_message(
                    f'Invalid trip status: {", ".join(invalid_statuses)}',
                    f'حالة الرحلة غير صالحة: {", ".join(invalid_statuses)}',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            queryset = queryset.filter(status__in=trip_statuses)

        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        
        # Serialize
        serializer = TripWithStopPointSerializer(
            page_obj,
            many=True,
            context={'request': request, 'account_type': 'passenger'}
        )

        message = get_bilingual_error_message(
            'Trips retrieved successfully.',
            'تم جلب الرحلات بنجاح.',
            locale
        )

        return Response({
            'success': True,
            'message': message,
            'data': {
                'trips': serializer.data
            },
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'page_size': paginator.per_page
            }
        }, status=status.HTTP_200_OK)


class PassengerTripDetailView(EMADBaseView):
    """
    Get trip details by ID
    GET /api/passenger/trips/{id}/
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['get']

    def handle_get(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            passenger = user.passenger_profile
        except Passenger.DoesNotExist:
            message = get_bilingual_error_message(
                'Passenger profile not found.',
                'ملف الراكب غير موجود.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.select_related(
                'base_driver__user',
                'base_driver__normal_driver__vehicle',
                'car_type',
                'airport',
                'passenger__user'
            ).prefetch_related('stop_points').get(
                id=trip_id,
                passenger=passenger
            )
        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found or you do not have permission to view it.',
                'الرحلة غير موجودة أو ليس لديك إذن لعرضها.',
                locale
            )
            return create_not_found_response(message, locale)

        serializer = TripWithStopPointSerializer(
            trip,
            context={'request': request, 'account_type': 'passenger'}
        )

        message = get_bilingual_error_message(
            'Trip details retrieved successfully.',
            'تم جلب تفاصيل الرحلة بنجاح.',
            locale
        )

        return Response({
            'success': True,
            'message': message,
            'data': serializer.data,
            'pagination': None
        }, status=status.HTTP_200_OK)


class PassengerCancelTripView(EMADBaseView):
    """
    Cancel trip with refund policy
    POST /api/passenger/trips/{id}/cancel/
    
    Refund Policy:
    - Cancellations made more than 24 hours before trip time → Fully refundable
    - Cancellations made within 24 hours of trip time → Non-refundable
    - No-shows → Non-refundable
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsPassenger]
    http_method_names = ['post']

    def handle_post(self, request, trip_id):
        locale = get_locale(request=request)
        activate(locale)
        user = request.user

        try:
            passenger = user.passenger_profile
        except Passenger.DoesNotExist:
            message = get_bilingual_error_message(
                'Passenger profile not found.',
                'ملف الراكب غير موجود.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            trip = Trip.objects.select_related(
                'passenger__user',
                'base_driver__user'
            ).get(
                id=trip_id,
                passenger=passenger
            )
        except Trip.DoesNotExist:
            message = get_bilingual_error_message(
                'Trip not found or you do not have permission to cancel it.',
                'الرحلة غير موجودة أو ليس لديك إذن لإلغائها.',
                locale
            )
            return create_not_found_response(message, locale)

        # Check if trip can be cancelled
        if trip.status == 'cancelled':
            message = get_bilingual_error_message(
                'This trip has already been cancelled.',
                'تم إلغاء هذه الرحلة بالفعل.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        if trip.status == 'completed':
            message = get_bilingual_error_message(
                'Cannot cancel a completed trip.',
                'لا يمكن إلغاء رحلة مكتملة.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        # Calculate trip datetime
        trip_datetime = timezone.make_aware(
            datetime.combine(trip.trip_date, trip.trip_time)
        )
        now = timezone.now()
        time_until_trip = trip_datetime - now

        # Determine refund eligibility
        is_refundable = False
        refund_reason = None

        if time_until_trip > timedelta(hours=24):
            # More than 24 hours before trip → Fully refundable
            is_refundable = True
            refund_reason = get_bilingual_error_message(
                'Cancellation made more than 24 hours before trip time.',
                'تم الإلغاء قبل أكثر من 24 ساعة من وقت الرحلة.',
                locale
            )
        elif time_until_trip > timedelta(0):
            # Within 24 hours → Non-refundable
            is_refundable = False
            refund_reason = get_bilingual_error_message(
                'Cancellation made within 24 hours of trip time. No refund available.',
                'تم الإلغاء خلال 24 ساعة من وقت الرحلة. لا يوجد استرداد.',
                locale
            )
        else:
            # Trip time has passed (no-show) → Non-refundable
            is_refundable = False
            refund_reason = get_bilingual_error_message(
                'Trip time has passed. No refund available for no-shows.',
                'لقد انتهى وقت الرحلة. لا يوجد استرداد للغياب.',
                locale
            )

        # Process refund if eligible and payment was made
        refund_processed = False
        refund_amount = None
        refund_error = None

        if is_refundable and trip.is_paid and trip.stripe_payment_intent:
            try:
                from apps.earnings.services.refund_rules import RefundRulesService
                from decimal import Decimal
                import uuid
                
                # Generate idempotency key for refund
                refund_idempotency_key = f"refund_{trip.id}_{uuid.uuid4().hex}"
                
                # Create refund with idempotency key
                refund = stripe.Refund.create(
                    payment_intent=trip.stripe_payment_intent,
                    idempotency_key=refund_idempotency_key
                )
                
                refund_processed = True
                refund_amount = Decimal(str(refund.amount / 100))  # Convert from cents to currency units
                
                # Process refund ledger entries
                try:
                    driver_refund, company_refund = RefundRulesService.process_refund(
                        trip=trip,
                        refund_amount=refund_amount,
                        stripe_refund_id=refund.id
                    )
                    logger.info(f"Refund processed for trip {trip.id}: refund_id={refund.id}, amount={refund_amount}, driver_refund={driver_refund}, company_refund={company_refund}")
                except Exception as e:
                    logger.error(f"Error processing refund ledger for trip {trip.id}: {str(e)}", exc_info=True)
                    # Continue with cancellation even if ledger entry fails
                
            except stripe.error.StripeError as e:
                refund_error = str(e)
                logger.error(f"Stripe refund error for trip {trip.id}: {str(e)}")
                # Continue with cancellation even if refund fails
                # Admin can process refund manually if needed
            except Exception as e:
                refund_error = str(e)
                logger.error(f"Error processing refund for trip {trip.id}: {str(e)}", exc_info=True)

        # Update trip status
        trip.status = 'cancelled'
        trip.save(update_fields=['status'])

        # Prepare response data
        response_data = {
            'trip_id': trip.id,
            'status': trip.status,
            'is_refundable': is_refundable,
            'refund_eligible': is_refundable,
            'refund_reason': refund_reason,
        }

        if refund_processed:
            response_data['refund_processed'] = True
            response_data['refund_amount'] = str(refund_amount)
            message = get_bilingual_error_message(
                'Trip cancelled successfully. Refund has been processed.',
                'تم إلغاء الرحلة بنجاح. تم معالجة الاسترداد.',
                locale
            )
        elif is_refundable and trip.is_paid:
            if refund_error:
                response_data['refund_error'] = refund_error
                message = get_bilingual_error_message(
                    'Trip cancelled successfully. However, refund processing encountered an error. Please contact support.',
                    'تم إلغاء الرحلة بنجاح. ومع ذلك، واجهت معالجة الاسترداد خطأ. يرجى الاتصال بالدعم.',
                    locale
                )
            else:
                message = get_bilingual_error_message(
                    'Trip cancelled successfully. No payment was made, so no refund is needed.',
                    'تم إلغاء الرحلة بنجاح. لم يتم الدفع، لذلك لا حاجة للاسترداد.',
                    locale
                )
        else:
            message = get_bilingual_error_message(
                'Trip cancelled successfully. No refund available per cancellation policy.',
                'تم إلغاء الرحلة بنجاح. لا يوجد استرداد متاح وفقاً لسياسة الإلغاء.',
                locale
            )

        if refund_processed and refund_amount is not None:
            refund_note_en = (
                f"A refund was processed to your original payment method. Amount: £{refund_amount}."
            )
        elif is_refundable and trip.is_paid and refund_error:
            refund_note_en = (
                f"Refund was eligible but processing failed ({refund_error}). "
                "Please contact support if you were charged."
            )
        elif is_refundable and trip.is_paid:
            refund_note_en = (
                "Cancellation was more than 24 hours before the trip; no payment refund was processed "
                "(or no Stripe payment was on file)."
            )
        elif not is_refundable and trip.is_paid:
            refund_note_en = (
                "Per policy, no refund applies for this cancellation (within 24 hours of pickup "
                "or after scheduled time)."
            )
        else:
            refund_note_en = "No payment refund applies (trip was unpaid or no card charge)."

        try:
            send_passenger_trip_cancellation_to_passenger(user, trip, refund_note_en)
            send_passenger_trip_cancellation_to_admin(trip, refund_note_en)
        except Exception as e:
            logger.warning(
                "Failed to send passenger cancel emails for trip %s: %s", trip.id, e
            )

        return Response({
            'success': True,
            'message': message,
            'data': response_data,
            'pagination': None
        }, status=status.HTTP_200_OK)

