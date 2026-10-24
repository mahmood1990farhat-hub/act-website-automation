# ACT cancellation policy integration checkpoint — 24 October 2026

**Candidate only. No merge, activation, effective date or payment authorisation.**

Owner accepted the customer review wording “for now” and requested continuation.
The accepted direction is customer draft v0.2 in PR #101, commit
`5618d56e111510e7cd1e32ecf524f67c34bcd9b7`, source blob
`4d95d04461f948754f72e267bea362c04c6ed513`. This acceptance is not a legal
certification, agreement to retrospectively change old bookings, or deployment approval.
The separate three-hour online-booking lead time is untouched.

## Source inspection and preservation

Reviewed recent PRs/heads #100 (98fc471, 20 browser cases), #101 (5618d56),
#102 (2a66095, successful isolated production build), issue #99 and existing
refund-related PRs before creating this candidate. Production baseline for this
backend-only branch is #98 `82c0b14ad2a71e1ce3d8d1df3527431b698ac461`.
The frontend subtree on this backend branch is NOT the frontend release candidate;
do not deploy that subtree or mistake the draft branch for a combined release.

Inspected at the exact backend baseline:
- `apps/trips/urls.py`, blob `1425c8c9fce94dda88fe78476c488fb2be7a5fcf`, and
  `apps/trips/passenger_urls.py`, blob `07f917dc8346bb6e1097f86066f77b3a50fd1bcc`,
  both route passenger cancellation to `PassengerCancelTripView`.
- `apps/trips/views/passenger_trips.py`, blob `bf47142b235d0879426d11bed29168f117b4be17`,
  uses >=3h full automatic refund and otherwise manual review. The Stripe call
  omits a partial amount and creates a new UUID idempotency key per request;
  response/email text still mentions three hours. The view does not record a
  new accepted-terms version or a durable first cancellation-receipt operation.
- The older `apps/trips/views/cancel.py`, blob `59c3309f052509bd0100e00d87b5f7b17b960e4d`,
  also contains full-refund code but is NOT the handler wired by those two routes.
  No claim is made about uninspected alternative entry points.
- `apps/trips/models/trip.py`, blob `04b7c188eaaa919886a6a265b8d076db142b610f`,
  has `booking_details` JSON, refund fields and `cancelled_at`, but no dedicated
  accepted cancellation-policy version field. A driver reassignment also uses
  cancellation fields: do not confuse it with passenger cancellation receipt.
- `apps/earnings/services/refund_rules.py`, blob `93bc189709b62c01a84346623f538656d296ba77`,
  addresses internal driver/company ledger allocation. It is not a substitute for
  passenger entitlement, and this candidate does not replace or duplicate it.

These are source findings, not live-server or live-payment observations. All
existing files, routes, snapshots, ledgers, keys and policy documents stay unchanged.

## Completed bounded component

`apps/trips/services/cancellation_policy.py` is a pure preview function. It has no
Django, Stripe, database, settings, clock, task or email dependency and is not
imported by a view, webhook or production entry point. It introduces no migration,
feature flag or default policy selection. `CANDIDATE_POLICY_VERSION` is only a
candidate identifier, not evidence a booking accepted it or that it is effective.

For explicitly identified new-policy passenger cancellations before pickup:

| Elapsed notice from ACT receipt to confirmed pickup | Standard refund |
| --- | --- |
| More than 24 hours | 100% |
| More than 12 hours and at most 24 hours | 50% |
| At most 12 hours | 0% |

The standard schedule is distinct from an assessed outcome. Retention below a
full refund needs a reviewed net loss and a reference; it is capped at the lower
of the schedule deduction and reviewed loss. Missing evidence produces a review
result with **no final refund amount**, not automatic denial. The reference alone
does not prove authority or fair losses: the later trusted admin process must do so.
This implements the safeguard in accepted draft section 4, not an additional
commercial rule or legal certification.

Amounts are integer GBP pence based on captured payment for the cancelled trip/leg,
not quoted fare. An odd-penny 50% calculation rounds up for the customer; this is a
proposed conservative engineering convention to include in final release review.
Prior refunded amounts are subtracted from the cumulative target without negative
refunds or clawback; this is not concurrency/payment-reconciliation protection.

Unknown/missing/legacy policy IDs are not silently given new bands. A no-show,
past pickup, started/completed/cancelled journey or unrelated reason requires review.
An ACT failure to supply the whole unperformed journey is a separate full-refund
case; driver rejection/reassignment must never be mapped to it automatically.
Unpaid journeys have zero refund due. The helper does not refuse cancellation or
alter a trip status merely because online refund assessment needs review.

Timezone-aware inputs are converted to UTC before elapsed-time comparison.
Nonexistent local times are rejected. Upstream parsing must resolve ambiguous
local times explicitly, including the DST fold, and preserve the confirmed pickup
and first received cancellation timestamp. Staff response time is never an input.

## Focused verification

33 new standard-library unit tests passed locally, including subcases for exact
12h/24h and one microsecond either side, odd pence, loss caps/zero losses, prior
refunds, unknown/old versions, ACT failure, no-show/elapsed pickup, unpaid/invalid
money/state/currency, UK spring/autumn transitions and repeated-hour fold. A small
1–99-pence grid checks amount bounds. The test file imports only this candidate
module; no Django setup, provider credentials or real customer data are used.
Hosted results are separate and must be read before claiming CI passed.
Existing UI/browser/build and payment tests were NOT repeated for this calculation
component, and their pass does not establish end-to-end refund integration.

## Remaining implementation sequence — same task, not a parallel payment system

1. **Persist accepted terms before accepting payment.** Inspect existing quote,
   PendingPayment, webhook and Trip creation paths and reuse them. Capture a
   server-selected policy version, effective version/hash, acceptance timestamp,
   locale and immutable priced trip/leg allocation. Do not trust client-supplied
   policy IDs or retroactively backfill this new ID onto old bookings. Verify old
   terms from actual available evidence; unresolved histories go to support.
2. **One cancellation/refund operation.** Reuse the two routed passenger entry
   points through one reviewed service. Persist first cancellation receipt and
   assessment under database concurrency protection. Use a durable operation ID,
   stable provider idempotency key and explicit incremental refund amount; reconcile
   captured/refunded/pending/disputed payment state. Reserve pending amounts so
   retries cannot over-refund. Reconcile provider status before claiming completed
   refund, and apply internal ledger entries once. Reuse existing earnings logic
   where valid; paid-driver/payout handling does not remove passenger rights.
3. **One public policy release.** Align reviewed customer source, appropriate
   translations, PDFs and hashes, FAQ, checkout, cancellation UI and confirmation
   emails/PDFs with booking-specific accepted terms. Display both scheduled and
   reviewed amounts honestly. Preserve the three-hour booking lead time, ACT-failure
   remedies and old booking terms. Do not publish the review pack's internal holds.
   Driver policies, company/privacy facts and physical browser acceptance remain
   as already tracked; accepted wording does not invent unresolved facts.
4. **Bounded integration checks and release.** Once wired, check old/new version
   routing, first-receipt timing, 12h/24h boundaries, a mocked partial refund,
   stable retry/concurrency and failed/pending payment outcomes, plus changed text
   and links. No real payment/refund or repeated full onboarding tests are needed.
   Separate exact-revision deployment approval remains required.

Automation coordination: the shared backend is the owner of financial calculation
and payment execution. n8n/agents must consume the canonical outcome/event and may
route exceptions; they must not implement another refund calculator or call Stripe
independently for the same cancellation. Coordinate event/schema changes in the ACT
automation workstream before activation. No n8n workflow is changed by this candidate.

## Primary references checked for the implementation design

These explain implementation constraints; they do not establish ACT operational facts.
- Stripe refunds: https://docs.stripe.com/refunds — partial amounts, original-charge
  upper bound and pending/failed outcomes need handling by the future executor.
- Stripe idempotency: https://docs.stripe.com/api/idempotent_requests — reuse the
  operation's key and reconcile rather than creating a new key on each retry.
- Python datetime: https://docs.python.org/3/library/datetime.html — aware datetime
  arithmetic; converting both instants to UTC avoids wall-time DST comparisons.
- CMA cancellation guidance: https://www.gov.uk/government/publications/cancelling-goods-or-services-guide-for-consumers/cancelling-goods-or-services
  — preserve the draft's reasonable-loss/mitigation safeguard. Owner loss evidence
  and appropriate legal/fairness review have not been supplied by this code task.

**Status: calculation component implemented and locally tested; live integration,
policy publication, merge and deployment NOT performed. Do not close issue #99.**
