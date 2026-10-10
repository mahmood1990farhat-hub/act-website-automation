# Accepted driver payout protection — 9 October 2026

Continuation of draft PR #83 at `7c8aa85f90ef7f75e11232783cc0138a358f59c5`. The prior CI #331 belongs to that earlier candidate; it is not evidence for this revision. No new branch/workflow/app, production migration, setting change, payout or deployment is performed here.

## Implemented in this slice

* Add private DriverPayoutAgreement records to the existing earnings app. Each acceptance records the driver, ACT deduction rate, gross/commission/net GBP amounts and timestamp. Only one unreleased agreement per trip is permitted. Financial terms cannot be rewritten through model/queryset update or delete paths; release retains the record. There is no driver/passenger agreement-management endpoint.
* The existing driver acceptance endpoint captures these terms in the same transaction as assignment and accepted status, after the existing eligibility checks. It returns only the locked driver earnings and agreement reference in addition to its existing status fields. Duplicate/competing acceptance cannot create competing agreements.
* Admin commission commands and acceptance acquire the same PostgreSQL configuration lock before driver and trip processing. Acceptance uses a fresh driver row and locks the selected rate. Driver NO KEY UPDATE locking permits ledger foreign-key inserts during completion. The previously cached membership driver is refreshed under its row lock before validating exclusivity.
* Driver cancellation releases terms atomically with the existing trip release. When a pending journey is subsequently reaccepted, any earlier terms are retained as released history and a new agreement is captured for the new accepting driver. Existing admin reassignment policies themselves are not redesigned here.
* The existing driver earnings display prefers the agreement rather than recalculating accepted journeys from today's rate. The completion calculator uses the same stored money values and locks the trip before its existing idempotency check. It refuses driver/fare mismatches rather than silently replacing agreed terms. Already-created ledgers remain unchanged.
* New management commands may change rates/group membership for unfinished accepted journeys only when a matching agreement protects them. Historical or pending assigned journeys without matching terms remain blocked; the additive migration does not invent historical accepted rates or rewrite old ledgers.

Money is calculated with Decimal: driver share rounded to a penny using ROUND_HALF_UP and ACT amount as the remainder, so both sum exactly to the passenger fare. This is used for pending previews and new agreements. The historical no-agreement completion path is retained unchanged.

## Required verification

The existing CI commission step explicitly includes `apps.earnings.tests.test_payout_agreements`. Its scenarios exercise the actual acceptance, cancellation, journey progression, completion, serializer and admin APIs; 0/100 percent and penny rounding; rejection/rollback and immutable terms; legacy vehicle-rate precedence; old unsnapshotted assignments; and two bounded PostgreSQL multi-connection concurrency cases. Provider delivery/tracking boundaries are mocked or use existing isolated CI settings, not production services. Read the exact revised run and review findings before accepting this slice.

## Release boundaries still open

PR #83 remains DRAFT; `ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED` remains false by default. This slice does NOT enable live saving. The next dependency is the explicit transition from legacy vehicle-based rules to the approved global/individual/group model, including inactive group semantics. No old rates are deleted or silently overruled here. Before release, review old assigned journeys without captured terms and any legacy configuration-write paths. Initial rates, scheduled changes, pre-acceptance offer-version acknowledgement, bonuses/reimbursements and third-party settlements remain separate agreed work.

The existing driver trip serializer still has its pre-existing broad response contract. This slice stabilizes the earnings fields; it does NOT claim that the separate passenger-fare/commission privacy migration is complete. That API/app compatibility task remains required before new driver finance/dispatch rollout.

## ACT AI Automation handoff

Read this PR/CI as the shared development record. Only this workstream owns the backend money calculation, agreement creation, admin changes and release. The mobile-development agent may review contracts and evidence, but must not write rates, memberships or payouts or create a competing dispatch/commission engine. No n8n or Driver v2 diagnostic changes. This note is a GitHub handoff, not a claim of direct delivery into another ChatGPT conversation.

## Driver API contract hardening — 10 October 2026

The existing paid/pending driver-offer endpoint now filters by the driver's exact vehicle class and capacity. Pending admin-reserved jobs are visible only to their selected driver. An accepted job disappears from every driver's available list; cancellation returns the job to other eligible drivers while excluding the cancelling driver. These behaviours use the existing backend endpoints, not a second dispatch system.

The driver offer, assigned-trip list/detail and shared user-trip serializer now omit passenger gross fare, pricing breakdown, Stripe identifiers and refund/payment details for driver-facing responses. Driver earnings remain available through the existing driver payout display. Passenger-facing trip responses retain their own fare fields. Former drivers cannot retrieve a reassigned trip via the shared user-trip listing. New isolated regression tests cover these boundaries.

**Release gate:** the above changes are committed in draft PR #83, not merged or deployed. Android client compatibility, nested booking_details privacy, and all remaining driver-facing endpoints require review before any mobile release. ACT AI Automation may review CI and propose issues but must not create parallel payout or dispatch logic.
