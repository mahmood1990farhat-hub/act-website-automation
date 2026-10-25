# ACT checkout-to-confirmation terms wiring - 25 October 2026

**Review candidate only. No production activation, policy effective date or deployment.**

## Preserved baseline and completed scope

This backend-only follow-on starts from PR #104 at
`4c2bf2447463dffe85ba6f30183a68ec71e5d981`. Its booking-contract service,
models, additive migration and 31-case storage result are unchanged. PR #103's
33-case calculator and PR #100/#101/#102's UI, policy and build work are unchanged.
Do not deploy the frontend subtree from this backend branch.

Latest PR heads, the prior successful CI job and exact source blobs were checked
before editing. Base `initiate_payment.py` blob:
`70b6c378e9db67ed04fdc36b691bd9f0bd74d033`; base payment `views.py` blob:
`d5156d15936c467166a2c9b455056216116043c8`. Local copies matched these hashes
before the narrow handler insertions. No dependency versions were changed.

The existing registered and guest initiation handlers now call the same terms
adapter before creating a PaymentIntent. Existing amount calculation, capacity,
permissions, contact validation, response shape and provider idempotency-key format
remain in place. The signed payment-success handler binds the accepted terms in
its existing database transaction before the pending-payment row is deleted.
Duplicate success paths verify already-bound acceptance rather than recreating it.

## Explicitly disabled rollout

`ACT_BOOKING_TERMS_CHECKOUT_ENABLED` defaults to False when absent. It must be a
literal boolean; invalid configuration does not silently opt out. No setting,
published release, PDF, locale manifest or effective date is introduced here.
The existing service still requires `ACT_BOOKING_TERMS_RELEASE` to identify an
actually published/effective reviewed document with matching text/PDF hashes.
Do not enable this candidate separately from the coherent cancellation release.

With the flag off, both payment routes retain legacy behaviour and do not assign
new terms. The adapter strips its reserved `_act_booking_terms` key from submitted
booking details and, when enabled, writes the server-controlled requirement marker.
A customer cannot disable capture by sending `required: false` or select a policy
through a booking-details field. No old record is backfilled.

Future frontend contract (not implemented by this backend-only patch):
`booking_terms_acknowledgement` must exactly match the server release's
`accepted: true`, `terms_version`, `terms_sha256` and `locale`. The server records
the request-receipt time and authoritative priced pickup/amount. The UI must actually
present the matching terms and receive a deliberate acknowledgement; an API field
alone is not proof that the customer was shown them. Missing, stale, false or forged
acknowledgements stop before the provider call. Neither review-pack text nor a
browser-supplied timestamp becomes a published policy.

UK local pickup is converted to UTC only where the wall time identifies one instant.
Nonexistent or repeated-hour times are held for explicit resolution, not silently
assigned a fold. A customer-facing ambiguity-resolution flow remains a release item.
The three-hour booking lead time is unchanged.

## Fulfillment, recovery and legacy protection

Precharge capture uses the existing durable database service. PaymentIntent failure
does not delete the accepted evidence or claim a paid Trip. No payment is attempted
if capture cannot commit. The new helper itself makes no network or refund call.

Fulfillment follows the saved checkout requirement, not today's rollout flag. An
already accepted checkout still binds if the flag is subsequently paused. A legacy
pending payment without acceptance remains legacy, even if the flag is later enabled.
For an accepted checkout, a verified settled GBP amount, identity and the accepted
snapshot must match. Missing required acceptance or corruption raises inside the
existing fulfillment transaction: Trip creation rolls back, pending evidence remains,
and the webhook returns non-success for retry. There is no automatic refund or silent
policy downgrade. Operations must investigate persistent fulfillment holds before
replaying events; genuine captured money is not erased by a failed database transaction.

Duplicate signed success notifications keep one booking and one acceptance, including
concurrent deliveries. Existing confirmation-task requeue/idempotency behaviour is
preserved; this patch does not send additional mail itself or claim bank settlement.

## Focused tests and their limits

The candidate adds 24 tests covering both actual DRF initiation handlers, real
PostgreSQL records/transactions and real signature verification on synthetic Stripe
webhooks. Maps/price calculation/capacity and external provider/notification boundaries
are mocked; this is not a pricing, browser, live-Stripe or whole-site retest. Outbound
non-loopback socket connections are blocked during tests.

Cases include precharge commit ordering; default-off preservation; marker tampering;
missing/false/stale acknowledgement; missing/unpublished/future/incorrect-hash release;
malformed activation setting; original registered-route authentication; database and
provider failure; guest/registered binding; rollout pause and legacy completion;
duplicate and concurrent signed success; missing/corrupted acceptance; wrong or
unsettled payment facts; invalid signature/payment failure; amended priced pickup;
and UK clock-change ambiguity.

Local AST/compilation and workflow-shell checks are supplementary. The local container
has no Django/PostgreSQL, so no local database execution is claimed. Actual hosted
results must be read before recording a pass. Preserve previous test evidence; no
repeated onboarding, calculator, storage or full frontend suite is requested.

## Remaining before the new policy can become effective

1. Finish the existing cancellation/refund execution path, authenticated provider
   reconciliation, admin review, external/failed/uncertain refund recovery and ledger
   posting once. Existing cancellation handlers are untouched and still use the old
   rule. This checkout flag must stay disabled until that coordinated integration is
   accepted. One new terms record does not implement a full refund process.
2. Publish only appropriately reviewed customer-facing policy content; align locale
   text/PDF hashes, terms-discovery and acknowledgement UI, cancellation screens and
   confirmations. ACT-specific policy-publication facts and fairness review remain as
   tracked in issue #99. Do not publish internal review notes.
3. Review the complete candidate on desktop then physical mobile web, run only the
   affected integration checks, and obtain separate exact-revision deployment approval.
   The prior payments.0003 migration is a deployment dependency; no new migration is
   added here and none has been applied to production by this task.

Automation ownership remains the shared backend under act-ai-workflows issue #2.
No new event contract, acknowledgement, n8n workflow, native-app change, live payment,
refund, email, VPS command or service change is implied.

Primary implementation references checked on 25 October 2026:
- https://docs.djangoproject.com/en/4.2/topics/db/transactions/ (durable capture and
  atomic fulfillment; this documentation also flags 4.2 as no longer supported).
- https://docs.stripe.com/webhooks (signature checks, duplicates and retries).

The existing Django support/security risk remains recorded separately; no silent
framework upgrade is included in this bounded patch.
