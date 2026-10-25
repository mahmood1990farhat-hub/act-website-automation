"""Existing passenger route plus permission-controlled review/reconciliation APIs.

No browser-supplied amount, policy version, timestamps or provider facts control
payment. Unknown historic terms are retained for review rather than reclassified.
"""
import logging

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.booking_contracts import ContractConflict
from apps.payments.models import CancellationCase, RefundReservation
from apps.payments.cancellation_flow import (
    managed_booking, passenger_filter, stop_passenger_journey, process_stopped_case,
    public_outcome, _staff,
)
from apps.trips.models import Trip
from apps.trips.views.passenger_trips import PassengerCancelTripView as LegacyCancelView
from utils.common import get_locale

logger = logging.getLogger(__name__)


class CancellationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'This cancellation needs ACT support review.'


def _message(outcome, locale):
    if outcome['refund_processed']:
        return ('تم إلغاء الرحلة. أكد مزود الدفع الاسترداد؛ قد يستغرق وصوله إلى البنك وقتاً إضافياً.'
                if locale == 'ar' else
                'Journey cancelled. The payment provider confirmed the refund; bank credit may take longer.')
    if outcome['review_required']:
        return ('تم إلغاء الرحلة. الاسترداد قيد المراجعة، وليس مرفوضاً تلقائياً.'
                if locale == 'ar' else 'Journey cancelled. The refund needs review; it has not been automatically refused.')
    return ('تم إلغاء الرحلة. يمكنك متابعة حالة الاسترداد مع دعم ACT.' if locale == 'ar'
            else 'Journey cancelled. Check the refund status below or contact ACT support.')


@method_decorator(never_cache, name='dispatch')
class PassengerCancelTripView(LegacyCancelView):
    def handle_post(self, request, trip_id):
        received = timezone.now()  # Capture server receipt before DB/provider work.
        try:
            trip = Trip.objects.get(passenger_filter(request.user), pk=trip_id)
        except Trip.DoesNotExist:
            raise NotFound('Journey not found.') from None
        if not managed_booking(trip):
            return super().handle_post(request, trip_id)
        try:
            case, created = stop_passenger_journey(trip_id, actor=request.user, received_at=received)
        except ContractConflict as exc:
            raise CancellationConflict(str(exc)) from None
        if created:
            try:
                from apps.trips.services.trip_tracking import stop_trip_tracking
                stop_trip_tracking(trip_id, reason='cancelled')
            except Exception:
                logger.warning('Managed cancellation tracking follow-up needed for trip %s', trip_id)
        try:
            process_stopped_case(case.pk)
        except Exception:
            # Cancellation was committed independently. Never turn a provider
            # outage into a failed cancellation, or leak provider error details.
            logger.warning('Managed refund follow-up needed for cancellation %s', case.pk)
        if created:
            try:
                from apps.payments.cancellation_assets import request_existing_cancellation_assets
                request_existing_cancellation_assets(case.pk)
            except Exception:
                # Never reinterpret a committed cancellation as failed because
                # document/email follow-up needs attention. No automatic resend.
                logger.warning('Existing cancellation assets need follow-up for case %s', case.pk)
        outcome = public_outcome(case.pk)
        return Response({'success': True, 'message': _message(outcome, get_locale(request=request)),
                         'data': outcome, 'pagination': None})


@method_decorator(never_cache, name='dispatch')
class CancellationReviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, receipt_id):
        _staff(request.user)
        if not CancellationCase.objects.filter(pk=receipt_id).exists():
            raise NotFound('Cancellation case not found.')
        case = CancellationCase.objects.get(pk=receipt_id)
        return Response({'success': True, 'data': {**public_outcome(receipt_id),
            'hold_reason': case.hold_reason, 'assessment': case.decision}})

    def post(self, request, receipt_id):
        _staff(request.user)
        if not CancellationCase.objects.filter(pk=receipt_id).exists():
            raise NotFound('Cancellation case not found.')
        if set(request.data) != {'reviewed_net_loss_pence', 'review_reference'}:
            raise CancellationConflict('Provide only the reviewed net loss and its evidence reference.')
        try:
            process_stopped_case(receipt_id, actor=request.user,
                reviewed_loss_pence=request.data['reviewed_net_loss_pence'],
                review_reference=request.data['review_reference'])
        except (ContractConflict, ValueError, TypeError):
            raise CancellationConflict('Review was not applied. Check the evidence and existing outcome.') from None
        # Provider failure propagates as a non-success review call, never a false
        # refund result. A claimed operation remains reserved for reconciliation.
        return Response({'success': True, 'data': public_outcome(receipt_id)})


@method_decorator(never_cache, name='dispatch')
class CancellationReconcileView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, receipt_id):
        _staff(request.user)
        if request.data:
            raise CancellationConflict('Reconciliation accepts no replacement amount or provider result.')
        op = RefundReservation.objects.filter(receipt_id=receipt_id).first()
        if op is None or not CancellationCase.objects.filter(pk=receipt_id).exists():
            raise NotFound('Managed refund operation not found.')
        from apps.payments.refund_provider import reconcile_reserved_refund
        try:
            reconcile_reserved_refund(op.pk)
        except ContractConflict:
            raise CancellationConflict('Refund still needs authorised reconciliation.') from None
        return Response({'success': True, 'data': public_outcome(receipt_id)})
