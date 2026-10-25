"""Internal Stripe boundary for reserved refunds; disabled until coordinated release.

No public refund endpoint, automatic retry, ledger posting or customer notification.
Only server-side identifiers are accepted. Provider facts are read with ACT's key.
A timeout after a dispatch claim requires reconciliation, never a fresh refund.
"""
import re
from uuid import UUID

import stripe
from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.payments.models import RefundReservation
from apps.payments.booking_contracts import (
    ContractConflict, PaymentObservation, claim_refund_dispatch, record_provider_refund,
)

REFUND_EVENTS = ('refund.created', 'refund.updated', 'refund.failed')
STATES = ('pending', 'requires_action', 'succeeded', 'failed', 'canceled')


def _plain(value):
    if hasattr(value, 'to_dict_recursive'):
        value = value.to_dict_recursive()
    elif hasattr(value, '_data'):
        value = value._data
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _id(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'_[A-Za-z0-9]+', value):
        raise ContractConflict('Invalid provider identifier')
    return value


def _integer(value):
    if type(value) is not int or value < 0:
        raise ContractConflict('Invalid provider money')
    return value


def _config():
    if getattr(settings, 'ACT_REFUND_PROVIDER_ENABLED', False) is not True:
        raise ContractConflict('Refund provider integration is disabled')
    live = getattr(settings, 'ACT_REFUND_PROVIDER_LIVEMODE', False)
    key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    if type(live) is not bool or not isinstance(key, str):
        raise ContractConflict('Invalid refund provider configuration')
    prefixes = ('sk_live_', 'rk_live_') if live else ('sk_test_', 'rk_test_')
    if not key.startswith(prefixes):
        raise ContractConflict('Provider key mode differs from configured mode')
    if connection.in_atomic_block:
        raise ContractConflict('Provider calls must be outside database transactions')
    return key, live


def _payment(payment_id, key, live):
    _id(payment_id, 'pi')
    p = _plain(stripe.PaymentIntent.retrieve(payment_id, expand=['latest_charge'], api_key=key))
    if (not isinstance(p, dict) or p.get('id') != payment_id
            or p.get('object') != 'payment_intent' or p.get('livemode') is not live
            or p.get('status') != 'succeeded' or p.get('currency') != 'gbp'):
        raise ContractConflict('Payment is not a matching settled GBP payment')
    c = p.get('latest_charge')
    if isinstance(c, str):
        c = _plain(stripe.Charge.retrieve(_id(c, 'ch'), api_key=key))
    if (not isinstance(c, dict) or c.get('object') != 'charge'
            or c.get('payment_intent') != payment_id or c.get('currency') != 'gbp'
            or c.get('livemode') is not live or c.get('paid') is not True
            or c.get('captured') is not True or c.get('status') != 'succeeded'
            or type(c.get('disputed')) is not bool):
        raise ContractConflict('Charge identity, capture or mode mismatch')
    _id(c.get('id'), 'ch')
    captured = _integer(c.get('amount_captured'))
    if captured <= 0 or captured != _integer(p.get('amount_received')):
        raise ContractConflict('Capture amount does not match payment')
    refunded = _integer(c.get('amount_refunded'))
    if refunded > captured:
        raise ContractConflict('Refunded charge exceeds capture')
    # Existing ACT checkout uses direct platform payments, not Connect transfers.
    if any(obj.get(field) for obj in (p, c)
           for field in ('on_behalf_of', 'transfer_data', 'application_fee_amount', 'application_fee')):
        raise ContractConflict('Connect payment requires a separately reviewed refund path')
    return c


def _refunds(payment_id, charge_id, key):
    """Read the complete bounded list, not the first ten embedded charge refunds."""
    rows, seen, after = [], set(), None
    for _ in range(10):
        args = {'payment_intent': payment_id, 'limit': 100, 'api_key': key}
        if after:
            args['starting_after'] = after
        page = _plain(stripe.Refund.list(**args))
        if (not isinstance(page, dict) or page.get('object') != 'list'
                or type(page.get('has_more')) is not bool or not isinstance(page.get('data'), list)):
            raise ContractConflict('Invalid provider refund page')
        for row in page['data']:
            if (not isinstance(row, dict) or row.get('object') != 'refund'
                    or row.get('payment_intent') != payment_id or row.get('charge') != charge_id
                    or row.get('currency') != 'gbp' or row.get('status') not in STATES):
                raise ContractConflict('Refund list identity or state mismatch')
            rid = _id(row.get('id'), 're')
            if _integer(row.get('amount')) == 0:
                raise ContractConflict('Zero-amount provider refund')
            if rid in seen:
                raise ContractConflict('Duplicate refund in paginated observation')
            seen.add(rid)
            rows.append(row)
        if not page['has_more']:
            return rows
        if not page['data']:
            raise ContractConflict('Empty unfinished refund page')
        after = page['data'][-1]['id']
    raise ContractConflict('Refund history exceeds bounded automatic review')


def observe_payment(payment_id):
    """Authenticated reads only. Unknown/inconsistent totals never authorise dispatch."""
    key, live = _config()
    first = _payment(payment_id, key, live)
    rows = _refunds(payment_id, first['id'], key)
    last = _payment(payment_id, key, live)
    fields = ('id', 'amount_captured', 'amount_refunded', 'disputed')
    if any(first[field] != last[field] for field in fields):
        raise ContractConflict('Provider balance changed during observation')
    succeeded = sum(r['amount'] for r in rows if r['status'] == 'succeeded')
    pending = sum(r['amount'] for r in rows if r['status'] in ('pending', 'requires_action'))
    if succeeded + pending > last['amount_captured']:
        raise ContractConflict('Provider refund totals exceed capture')
    if not pending and succeeded != last['amount_refunded']:
        raise ContractConflict('Charge and complete refund history disagree')
    return PaymentObservation(payment_id, last['amount_captured'], succeeded, pending,
                              timezone.now(), disputed=last['disputed'])


def _hold(operation_id):
    # Never overwrite a webhook result that won a race with a timed-out create.
    RefundReservation.objects.filter(pk=operation_id, status='in_flight').update(
        status='reconcile', updated_at=timezone.now())
    return RefundReservation.objects.get(pk=operation_id)


def _result(operation):
    return {'operation_id': str(operation.pk), 'status': operation.status,
            'provider_refund_id': operation.provider_refund_id,
            'amount_pence': operation.amount_pence,
            'review_required': operation.status in ('reconcile', 'failed', 'canceled', 'requires_action')}


def _persist(operation, raw, charge_id=None):
    p = _plain(raw)
    if (not isinstance(p, dict) or p.get('object') != 'refund'
            or not isinstance(p.get('metadata'), dict)
            or p['metadata'].get('act_refund_operation') != str(operation.pk)
            or (charge_id is not None and p.get('charge') != charge_id)):
        raise ContractConflict('Refund is not correlated to this ACT operation')
    # Validate before any hold; an unrelated response must never mutate this record.
    if (type(p.get('amount')) is not int or p['amount'] != operation.amount_pence
            or p.get('currency') != 'gbp' or p.get('payment_intent') != operation.payment_intent_id
            or p.get('status') not in STATES):
        raise ContractConflict('Refund fields differ from reserved operation')
    _id(p.get('id'), 're')
    with transaction.atomic():
        current = RefundReservation.objects.select_for_update().get(pk=operation.pk)
        if current.provider_refund_id not in (None, p['id']):
            raise ContractConflict('Provider refund identity changed')
        if current.status == 'reconcile' and current.provider_refund_id:
            return current  # A terminal conflict needs authorised accounting review.
        if current.status in ('succeeded', 'failed', 'canceled') and p['status'] != current.status:
            # This is a current provider GET, not an old webhook payload. Funds can
            # be returned later. Do not leave a misleading completed status or resend.
            current.status = 'reconcile'
            current.save(update_fields=['status', 'updated_at'])
            return current
        return record_provider_refund(current.pk, provider_result=p)


def dispatch_reserved_refund(operation_id):
    """One reserved attempt, not a passenger API or retry loop. All callers are internal."""
    key, _ = _config()
    if getattr(settings, 'ACT_REFUND_DISPATCH_ENABLED', False) is not True:
        raise ContractConflict('New refund dispatch is disabled')
    operation = RefundReservation.objects.get(pk=operation_id)
    if operation.status != 'prepared':
        return _result(operation)
    evidence = observe_payment(operation.payment_intent_id)
    payload = claim_refund_dispatch(operation.pk, evidence=evidence, claimed_at=timezone.now())
    if payload is None:
        return _result(RefundReservation.objects.get(pk=operation.pk))
    try:
        response = stripe.Refund.create(**payload, api_key=key)
        operation = _persist(operation, response)
    except Exception:
        # A network/parse/persistence failure cannot prove that no refund occurred.
        # Database failure to save this hold propagates; the committed claim remains.
        operation = _hold(operation.pk)
    return _result(operation)


def reconcile_reserved_refund(operation_id):
    """Read an already attempted refund; NEVER call Refund.create, even after 24h."""
    key, live = _config()
    operation = RefundReservation.objects.get(pk=operation_id)
    if operation.first_attempt_at is None or operation.status == 'prepared':
        raise ContractConflict('An unattempted reservation cannot consume a provider refund')
    charge = _payment(operation.payment_intent_id, key, live)
    if operation.provider_refund_id:
        raw = stripe.Refund.retrieve(_id(operation.provider_refund_id, 're'), api_key=key)
    else:
        rows = _refunds(operation.payment_intent_id, charge['id'], key)
        matches = [r for r in rows if isinstance(r.get('metadata'), dict)
                   and r['metadata'].get('act_refund_operation') == str(operation.pk)]
        if not matches:
            # Zero does NOT prove that a timed-out POST never executed.
            return _result(_hold(operation.pk))
        if len(matches) != 1:
            raise ContractConflict('Multiple refunds claim one ACT operation')
        raw = matches[0]
    operation = _persist(operation, raw, charge['id'])
    return _result(operation)


def handle_verified_refund_event(event):
    """Called ONLY after the existing endpoint verifies Stripe's raw-body signature.

    The event locates an operation; a current authenticated GET supplies its state.
    Foreign/unmanaged refunds are not adopted. Invalid matched events fail non-2xx.
    """
    if event.get('type') not in REFUND_EVENTS:
        return None
    if getattr(settings, 'ACT_REFUND_PROVIDER_ENABLED', False) is not True:
        return None
    _, live = _config()
    if event.get('livemode') is not live or event.get('account'):
        raise ContractConflict('Wrong mode/account for refund event')
    obj = (event.get('data') or {}).get('object') or {}
    if obj.get('object') != 'refund':
        raise ContractConflict('Refund event must carry a refund object')
    rid = _id(obj.get('id'), 're')
    metadata = obj.get('metadata') or {}
    if not isinstance(metadata, dict):
        raise ContractConflict('Invalid provider event metadata')
    marker = metadata.get('act_refund_operation')
    by_id = RefundReservation.objects.filter(provider_refund_id=rid).first()
    if marker:
        try:
            parsed = UUID(marker)
        except (ValueError, TypeError, AttributeError):
            raise ContractConflict('Invalid ACT refund operation marker') from None
        operation = RefundReservation.objects.filter(pk=parsed).first()
        if operation is None or (by_id is not None and operation.pk != by_id.pk):
            raise ContractConflict('ACT refund marker does not match local operation')
    else:
        operation = by_id
    if operation is None:
        return None
    if (obj.get('payment_intent') != operation.payment_intent_id
            or operation.provider_refund_id not in (None, rid)):
        raise ContractConflict('Event refund/payment does not match local operation')
    return reconcile_reserved_refund(operation.pk)
