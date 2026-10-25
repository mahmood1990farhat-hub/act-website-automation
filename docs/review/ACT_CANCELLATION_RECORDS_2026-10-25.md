# ACT booking terms and cancellation database boundary — 25 October 2026

DRAFT. No production deployment, live migration, refund, email or route activation.
Parent: tested calculator 5f309ea9441414ce76a1725d0d00b1497a67e177 (PR #103).
The original 33 calculation checks and existing UI/build evidence are preserved.
This backend branch's frontend subtree is NOT the accepted frontend candidate.

## Implemented scope

Three additive tables in payments migration 0003: BookingTermsAcceptance,
CancellationReceipt, RefundReservation. PendingPayment's existing class is byte-for-byte
preserved. No historical booking is backfilled with the new policy.

`capture_checkout_terms` saves server-selected terms text/version/content hash,
PDF hash/path, locale, first acknowledgement receipt, exact priced amount and
confirmed pickup before payment initiation. ACT_BOOKING_TERMS_RELEASE defaults
to absent; there is NO published release configuration in this candidate. Only an
explicit matching acknowledgement of a server-configured published/effective
release is accepted. Browser booking_details and policy IDs are not authority.
Only reviewed locale entries may be selected; no silent language fallback.
The supplied aware pickup instant must match the priced UK local date/time.

`bind_paid_terms` attaches that record to the paid Trip inside the existing
fulfillment transaction before PendingPayment is deleted. It verifies the bound
payment, amount, currency, passenger relation and pickup; repeated binding is
idempotent. Pending deletion sets only its relation to NULL; the accepted terms
survive. Unknown/old checkouts remain without a new accepted-policy record.
Checksums detect inconsistent stored snapshots; this is NOT cryptographic
protection from a database administrator. The service provides no snapshot-edit
operation; generic admin editing is deliberately not registered.

`record_cancellation_receipt` serializes on the trip row, retaining the first
recorded receipt across later retries. Conflicting reason or earlier discovered
receipt evidence requires review; this function does NOT cancel the Trip itself.
It must eventually be called from an authorized server boundary using ACT receipt
time, not a browser timestamp or later staff response time.

`prepare_refund_reservation` calls the existing calculator against stored terms,
not today's policy. It holds unknown terms, unsupported journey states and
unreviewed deductions. A reviewed loss needs an active staff reviewer and reference;
that reference does not itself prove fairness. It saves one refund reservation
and immutable request parameters per receipt, using integer GBP pence. Existing
records and paid-trip history are not repriced. Changed pickup details require
reviewed amendment evidence rather than silently moving a cutoff.

`claim_refund_dispatch` commits a single claim with a stable operation UUID/key
before a future provider call. It requires fresh reconciled payment facts, checks
capture/refund balance and blocks disputed/pending/changed payments. The five-minute
observation bound is a conservative candidate safety setting, not an owner business
rule. Concurrent claims return only one dispatch payload. No payment is sent here.
An uncertain in-flight operation is never automatically reissued, including after
Stripe's key-retention window. Failures require an explicit reconciliation/recovery
path, not a fresh key. Durable transaction guards reject calls inside another
uncommitted transaction at precharge/dispatch boundaries.

`record_provider_refund` checks provider refund ID, payment ID, exact amount,
currency and status. Pending/requires_action do not mean success. Duplicates and
older pending events cannot regress terminal state; contradictory final outcomes
require reconciliation. Financial ledgers and customer messages are NOT updated by
this internal storage layer. Existing RefundRulesService remains untouched.

## Important remaining integration — do not mistake storage tests for full rollout

The existing initiation views, webhook, cancellation views, admin screens and
provider calls are intentionally NOT edited yet. There are no signals/auto-hooks.
The migration is applied only to disposable test databases, not the live VPS.

1. Publish approved versioned customer documents/locale hashes only after the
   outstanding policy facts/review, then configure the server release and add
   explicit checkout acknowledgement. Wire capture to both existing registered
   and guest initiation paths BEFORE creating a PaymentIntent. The new storage
   APIs must never be exposed as unrestricted public model CRUD.
2. Wire bind_paid_terms inside create_trip_from_payment before pending deletion.
   Preserve existing payment/webhook/confirmation idempotency. Add focused tests
   of those actual routes, not another full onboarding/payment acceptance cycle.
3. Replace the currently routed cancellation execution atomically with this boundary;
   disable the old competing direct-refund path at that same release. Preserve
   legacy accepted terms and manual support. Wire authorized staff review, genuine
   fresh Stripe observations, provider execution, authenticated status reconciliation,
   ledger-once updates and truthful localized customer/admin outcomes. Current
   public endpoints still use the old cancellation implementation.
4. One reservation is supported per receipt in this candidate. Further adjustments,
   refunds made directly in Stripe, ambiguous dispatch outcomes, ledger recovery,
   paid-driver allocations and repeated final-state disagreements need the explicit
   recovery path before release. No claim of end-to-end duplicate-payment protection
   is made while the old public handler remains active. The stored successful
   provider state is not evidence the customer bank has credited funds.
5. Coordinate canonical outcomes with act-ai-workflows issue #2; no second n8n
   calculator/refund executor. Complete changed-path integration and desktop/physical
   mobile acceptance, then obtain separate exact-revision deployment approval.

## Verification

New TransactionTestCase suite targets PostgreSQL, not mocked persistence/SQLite:
precharge acknowledgement/config guards, exact preserved snapshot, paid binding,
pending cleanup survival, legacy/manual holds, receipt preservation, partial
reservation with staff review, stale/pending/disputed provider facts, durable
single dispatch, pending/failed/success transitions, constraints and three threaded
PostgreSQL races (receipt, reservation, claim). All test data is synthetic.
Runtime external socket connections are blocked except loopback database/cache.
No Stripe client is imported or invoked by the new service.

Local checks: Python AST/byte-compilation, YAML and shell syntax; Django/PostgreSQL
are not installed in the local container, so database outcomes must be taken from
the actual hosted workflow, not inferred. Hosted result is pending at this commit.
Existing requirements are version ranges, NOT a fully pinned lockfile; retain the
actual installed versions in CI evidence. No production dependencies are upgraded.

## Primary references consulted

- https://docs.stripe.com/api/idempotent_requests — v1 keys may be pruned after
  24 hours; a durable operation record and reconciliation are necessary.
- https://docs.stripe.com/refunds — explicit partial amounts, maximum original
  captured amount and pending/failed outcomes.
- https://docs.djangoproject.com/en/4.2/topics/db/transactions/ — durable outer
  atomic boundaries and commits before external effects.
- https://docs.djangoproject.com/en/4.2/ref/models/querysets/#select-for-update —
  database row locking and transaction tests.

Separate maintenance risk: backend requirements currently constrain Django to
4.2.x; its official documentation marks that series unsupported/insecure. This
candidate preserves the baseline rather than silently upgrading a production
framework. A supported-version/security review must be tracked separately and
is not resolved by these storage tests.
