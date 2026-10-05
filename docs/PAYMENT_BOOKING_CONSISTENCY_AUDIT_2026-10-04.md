# Payment to booking consistency audit — 2026-10-04

**Status: reliability fixes drafted on PR #71. Not merged/deployed. No real or test Stripe charge was executed in this session.**

## Reproduced risks

### 1. Verified Stripe success could be acknowledged even when booking creation failed
`stripe_webhook_view` called `handle_payment_succeeded`, but that handler caught all exceptions and returned normally. The webhook view then returned HTTP 200. A database/model failure could therefore leave Stripe paid while ACT had no Trip, while Stripe was told the event had been handled.

**Fix:** booking-processing exceptions now propagate to the webhook view, which returns HTTP 500 for a verified event that ACT could not process. Invalid signatures remain HTTP 400. Successful/idempotent processing remains HTTP 200.

### 2. Duplicate success delivery could duplicate side effects
`create_trip_from_payment` already looked up an existing Trip by unique `stripe_payment_intent`, but `handle_payment_succeeded` then ran PDF/email/internal/driver notification work whether the Trip was new or existing.

**Fix:** fulfillment returns `(trip, created)`. Duplicate/retried success events return the existing Trip and skip duplicate post-creation side effects.

Follow-up confirmation work adds durable per-trip passenger/internal email acceptance timestamps and a retryable Celery confirmation task. SMTP delivery remains at-least-once under the rare crash window after SMTP acceptance but before the database timestamp is committed; exactly-once external email delivery is not claimed.

### 3. Pending-payment metadata lookup was not bound to the PaymentIntent
When metadata supplied `pending_payment_id`, the code accepted that database row by ID without also checking its `payment_intent_id`.

**Fix:** metadata ID lookup now requires both PendingPayment ID and exact PaymentIntent ID. Fulfillment obtains a row lock while consuming the pending record and rechecks the unique Trip after waiting to handle concurrent deliveries.

### 4. Settled amount/currency was not compared with ACT's authoritative pending price
Trip creation trusted the PendingPayment price after receiving a success event without explicitly verifying the event's settled amount/currency against it.

**Fix:** before Trip creation, compare Stripe `amount_received` (fallback `amount`) and currency with PendingPayment `price_breakdown.total_cost` and currency. Mismatch fails fulfillment rather than creating a wrongly valued paid booking. Stripe amount creation now uses Decimal + ROUND_HALF_UP for deterministic pence conversion in both guest and signed-in initiation paths.

### 5. Frontend treated Stripe success as booking confirmation
The card form advanced immediately after `PaymentIntent.status === succeeded`, while the webhook could still be creating the Trip. The confirmation page also said confirmation details had already been emailed.

**Fix:** added a minimal read-only `/api/payments/booking-status/?payment_intent_id=...` endpoint returning only `confirmed`, `processing`, `unknown` or `invalid`; no customer/booking data is exposed. After Stripe success, the frontend disables back/resubmit, tells the passenger the paid booking is being finalised, and polls for the persisted paid Trip. Only after the Trip exists does it fire the Google Ads booking conversion and advance to booking confirmation. If fulfillment takes longer, it tells the passenger not to pay again rather than showing a retryable payment error.

The final confirmation wording now says confirmation details **will be sent** rather than claiming email delivery has already completed.

## Existing safeguards retained

- `Trip.stripe_payment_intent` is unique.
- `PendingPayment.payment_intent_id` is unique.
- Stripe initiation uses a PendingPayment-specific idempotency key.
- Guest and signed-in initiation both recalculate price server-side.
- Payment metadata includes PendingPayment ID, car ID/code, date/time, passenger count and currency.
- Multi-stop payment handoff was fixed in the previous audit slice so authoritative payment routing receives the same ordered stops.

## Tests added (committed, not yet executed here)

`apps/payments/test_webhook_reliability.py` covers:
- verified success processing failure -> HTTP 500;
- duplicate success -> no duplicate PDF/notification side effects;
- exact amount/currency verification;
- PendingPayment ID cannot be rebound to a different PaymentIntent.

Frontend source regression guard `tests/check-payment-fulfillment-safety.cjs` checks that successful Stripe payment waits for persisted booking status, blocks back/re-submit after capture, and fires the booking conversion only after booking confirmation.

## Required Stripe test-mode acceptance

1. Guest successful payment -> one PendingPayment -> one paid Trip -> one intended confirmation flow.
2. Signed-in successful payment -> same invariants.
3. Stripe duplicate/replayed `payment_intent.succeeded` -> same Trip, no duplicate side effects.
4. Simulated booking-creation failure -> webhook non-2xx; retry later creates the Trip once.
5. Amount/currency mismatch fixture -> no Trip created.
6. Declined card and failed authentication -> no paid Trip and passenger can safely retry.
7. Successful payment with delayed webhook -> UI blocks repeat payment and waits/communicates finalisation.
8. Multi-stop quote -> payment route/price/Trip stop records agree.
9. Browser refresh/back around payment and repeated review initiation; verify no accidental second paid booking.
10. Verify Google Ads conversion is emitted only after the paid Trip exists.

## Open before acceptance

- Execute backend tests/full suite and frontend build.
- Run Stripe test-mode webhook delivery/replay evidence against an isolated environment.
- Paid booking confirmation/PDF/internal email delivery now has retryable Celery processing and durable per-trip acceptance markers; execute this path with the real test SMTP/Celery environment before acceptance.
- Review abandoned PendingPayment cleanup/expiry and repeated pre-payment initiation behaviour.
