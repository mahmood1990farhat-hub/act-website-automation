# Managed cancellation route, review and accounting checkpoint

25 October 2026. Candidate only; no deployment, policy effective date or real refund.
Base: PR #106 `006bd4d68a326a948f2e430d19984fe43ad5a711`.
Preserve UI #100, policies #101, calculator #103, records #104 and checkout #105.
The frontend subtree on this backend branch is NOT the frontend release candidate.

## Completed code scope (runtime evidence separate)

Both existing passenger cancellation URL modules use one managed wrapper. An
unversioned/unmanaged booking retains the old handler while the new activation
switch is off. A stored acceptance, terms-required marker or cancellation record
can never fall back to that old direct-refund logic, even during a rollout pause.
The formerly unused unconditional full-refund handler is now a compatibility shim
which delegates to the same wrapper. No second policy calculator is introduced.

The server captures receipt time before work, reauthorises ownership inside a
Trip row lock, records the cancellation and commits status=cancelled BEFORE any
provider call. Payment failure does not roll back the journey stop. A guest email
match cannot grant cancellation rights over another registered passenger's trip.
Pending/accepted/driver-en-route trips can stop; active/completed/expired journeys
require support. A driver withdrawal is not treated as passenger cancellation.

Payments migration 0004 adds CancellationCase and RefundPosting; no old bookings
are backfilled. It also installs a PostgreSQL BEFORE UPDATE trigger scoped only
to managed cancelled journeys. This prevents stale ORM, bulk-update or SQL writes
from restarting/reassigning/repricing those trips, including when old code read a
previous state. Refund metadata writes remain allowed. The trigger is deliberately
stronger than a Python save override; its deployment/reversal requires review with
the exact migration. A failed stale driver write may still return the existing
handler's generic error; no improved driver-facing error text is claimed here.

For assessment, a verified stopped case projects its original unperformed state
into the existing calculator without actually reopening the Trip. Driver en route
maps to accepted for calculation only. Existing internal fixtures without a case
retain their old service contract; new routed executions always require a case.
No new percentages are inferred for a missing/unknown historical acceptance.

The admin review API requires an active staff account AND the explicit
payments.review_cancellationcase permission. Only net-loss pence and an evidence
reference are accepted; actor identity is taken from authentication. A reference
is not itself proof that the assessment is fair. Both positive and zero final
assessments are saved. Repeated decisions cannot silently change a reserved amount.
An initial 0% schedule without a reviewed loss remains review-required, not denial.

A provider result synchronises Trip refund status and posts the existing company
refund ledger once per managed RefundReservation. The posting and marker commit
atomically under Trip/reservation locks. Pending/failed/uncertain states do not
post. A posting failure can be repaired by authenticated read-only provider
reconciliation without another Refund.create. Existing driver earnings or
ambiguous/conflicting ledger history are held for accounting review rather than
speculatively debiting a driver or duplicating old entries. Late provider conflicts
remain on hold and do not automatically reverse an earlier ledger posting.

The provider hook does not send email. Customer responses distinguish cancellation,
review, pending and provider-confirmed refund; they do not promise bank credit.
English/Arabic response text is present, not a seven-language communication release.
Public and admin responses have no-store cache protection. No generic admin CRUD
is registered for accepted terms, cases or postings.

## Guards and rollout

`ACT_CANCELLATION_FLOW_ENABLED` activates managed handling for otherwise unversioned
bookings and defaults off. Existing accepted/managed records always remain managed.
Provider read/dispatch and checkout flags remain separate and off by default.
No settings, published terms, effective date or webhook subscription is added.
All migrations must be reviewed/applied as part of the eventual coordinated release;
flags alone do not remove that schema dependency. No production migration is run.

Actual endpoints introduced under the existing payments prefix:
- `cancellations/<receipt UUID>/review/`: permission-controlled GET/POST net-loss review.
- `cancellations/<receipt UUID>/reconcile/`: permission-controlled POST, no supplied
  amount or provider facts; authenticated GET reconciliation only, never a new refund.
These are backend endpoints, not a completed operator-facing React screen.

## Verification plan and source evidence

Exact latest PR/branch heads and the prior 28-test provider artifact were checked
before editing. Retained artifact SHA-256 matched
177cf9d7bb2285ec0ddd462d64d8bdfddcefde5e1a5236e1f16ce89c91b7078d.
Local reconstructed base files matched Git blobs before narrow edits:
models.py 8b4efda93c6929320644026a3a85ff3d6c8feb23;
booking_contracts.py bf8e7c6fc2ded2c8e2c5ba68a9a8769addff5daa;
refund_provider.py ba04e6369d30898b220d17a6a364ad8736605379.
The existing driver save guard and start handler were inspected to identify stale
write exposure. Existing calculator, checkout adapters, prices, policy drafts,
financial-rule service, driver onboarding and dependency constraints are unchanged.

New suite: 32 focused PostgreSQL/DRF methods, including three threaded races.
Uses synthetic fixture helpers, not imported previous test classes/methods. Actual
provider SDK methods and tracking are mocked; non-loopback sockets blocked.
Covers both routes, stop-before-money, authorised deductions/zero results, legacy
holds/disabled fallback, forgery/ownership, outages/timeouts, pending/signed success,
exactly-once posting and recovery, terminal conflict, stale/bulk writes and races.
AST/compile/YAML/Bash checks are local; hosted runtime/migration results must be
read before claiming pass. Local container has no Django/PostgreSQL. Old unrelated
browser/build/calculator/onboarding tests are not repeated by this workflow.

Primary references checked: Django 4.2 transactions/select_for_update and Stripe
refund/idempotency docs. Django 4.2 documentation warns it is unsupported/insecure;
that pre-existing upgrade/security release issue is not silently resolved here.

## Still open before production

This is not full website acceptance. Complete the admin browser interface and
customer confirmation/cancellation email/PDF delivery using booking-specific terms
and trustworthy delivery state. No live notification or email replay is performed.
Finish verified historical-terms/full-refund support, adjusted bookings, additional
refund adjustments, failed/uncertain/external-refund resolution and any necessary
ledger reversal/payout accounting. Current safe holds are not resolutions of those
exception cases. Operators must not work around them by creating a duplicate refund.

Source/PDF/locale/hash/checkout acknowledgement, policy-publication facts, physical
browser review and exact-revision deployment approval remain outstanding. External
Stripe Dashboard writes are not serialised by our local locks; operational ownership
and competing refund creation controls are required at rollout. Automation issue #2
remains the backend ownership coordination record; no n8n change or acknowledgement
is implied. No source and migration in this candidate may be independently enabled
while the published policy/UI still disagree. Keep issue #99 open.
