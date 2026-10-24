"""Versioned, calculation-only cancellation preview. NOT wired into live views.

No database, Stripe, settings, clock, email or task imports. A preview is never
payment authorisation. Persist/verify accepted terms and a durable refund operation
before integrating. Unknown/legacy versions must not inherit this new schedule.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

CANDIDATE_POLICY_VERSION = "act-cancellation-24h12h-v1"


@dataclass(frozen=True)
class RefundPreview:
    policy_version: str | None
    outcome: str
    standard_refund_percent: int | None
    standard_total_refund_pence: int | None
    assessed_total_refund_pence: int | None
    additional_refund_pence: int | None
    review_required: bool


def _pence(value: int, name: str) -> None:
    # Reject bools, floats and implicit string conversions at a money boundary.
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer number of pence")


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    instant = value.astimezone(timezone.utc)
    # Do not silently normalise a nonexistent local time at a DST transition.
    if instant.astimezone(value.tzinfo).replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError(f"{name} is a nonexistent local time")
    return instant


def preview_cancellation_refund(
    *,
    accepted_policy_version: str | None,
    confirmed_pickup_at: datetime,
    cancellation_received_at: datetime,
    captured_amount_pence: int,
    already_refunded_pence: int = 0,
    currency: str = "GBP",
    cancellation_kind: str = "passenger_cancellation",
    journey_status: str = "pending",
    reviewed_net_loss_pence: int | None = None,
    loss_review_reference: str | None = None,
) -> RefundPreview:
    """Return a proposed cumulative refund and its unpaid remainder, never pay it.

    Version must come from trusted, immutable accepted-terms evidence, not browser
    input, cancellation date or a default setting. Amount is captured money for
    this trip/leg, not a quote. Net loss must be reviewed, evidenced and already
    reduced for costs saved/replacement work; a reference is not proof of review.
    Half pennies are rounded UP in the customer's favour (engineering proposal).
    Unknown terms, no-show allegations and started journeys need separate review.
    """
    if accepted_policy_version is not None and not isinstance(accepted_policy_version, str):
        raise ValueError("accepted_policy_version must be a string or None")
    for value, name in ((captured_amount_pence, "captured_amount_pence"),
                        (already_refunded_pence, "already_refunded_pence")):
        _pence(value, name)
    if already_refunded_pence > captured_amount_pence:
        raise ValueError("already_refunded_pence exceeds captured amount")
    if currency != "GBP":
        raise ValueError("This candidate supports GBP only")
    if cancellation_kind not in ("passenger_cancellation", "act_unable_to_supply", "no_show", "other"):
        raise ValueError("Unknown cancellation_kind")
    if not isinstance(journey_status, str):
        raise ValueError("journey_status must be a string")
    pickup = _utc(confirmed_pickup_at, "confirmed_pickup_at")
    received = _utc(cancellation_received_at, "cancellation_received_at")
    if reviewed_net_loss_pence is None:
        if loss_review_reference is not None:
            raise ValueError("Loss reference requires a reviewed amount")
    else:
        _pence(reviewed_net_loss_pence, "reviewed_net_loss_pence")
        if not isinstance(loss_review_reference, str) or not loss_review_reference.strip():
            raise ValueError("A reviewed loss requires a review reference")

    def held(outcome: str, percent: int | None = None, standard: int | None = None) -> RefundPreview:
        return RefundPreview(accepted_policy_version, outcome, percent, standard, None, None, True)

    def assessed(outcome: str, percent: int, standard: int, total: int) -> RefundPreview:
        return RefundPreview(accepted_policy_version, outcome, percent, standard, total,
                             max(0, total - already_refunded_pence), False)

    if captured_amount_pence == 0:
        return assessed("unpaid_no_refund_due", 0, 0, 0)
    if journey_status not in ("pending", "accepted"):
        return held("journey_state_review_required")
    # A driver's rejection/reassignment is NOT an ACT failure-to-supply decision.
    if cancellation_kind == "act_unable_to_supply":
        return assessed("act_unable_to_supply_full_refund", 100,
                        captured_amount_pence, captured_amount_pence)
    if cancellation_kind != "passenger_cancellation":
        return held("cancellation_reason_review_required")
    if accepted_policy_version != CANDIDATE_POLICY_VERSION:
        return held("accepted_terms_review_required")

    notice = pickup - received  # Both UTC: elapsed hours, including clock changes.
    if notice > timedelta(hours=24):
        percent, standard = 100, captured_amount_pence
    elif notice > timedelta(hours=12):
        percent, standard = 50, (captured_amount_pence + 1) // 2
    else:
        percent, standard = 0, 0
    if notice <= timedelta(0):
        # A passed pickup time is not itself proof of a no-show or completed trip.
        return held("pickup_elapsed_review_required", percent, standard)
    if percent == 100:
        return assessed("standard_full_refund", percent, standard, standard)
    if reviewed_net_loss_pence is None:
        return held("fair_loss_review_required", percent, standard)

    retained = min(captured_amount_pence - standard, reviewed_net_loss_pence)
    total = captured_amount_pence - retained
    return assessed("reviewed_loss_capped_refund", percent, standard, total)
