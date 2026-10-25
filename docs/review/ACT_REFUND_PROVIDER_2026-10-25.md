# ACT refund provider boundary - 25 October 2026

**Candidate only. Not merged, deployed, activated or authorised for live refunds.**

## Preserved baseline and precise scope

Continue from checkout PR #105 `da7675033df54a2c0f13fa751ef931d3e059f547`, not
main or the frontend branch. Latest PR/head and existing 24-handler test evidence
were read before editing. PR #104's 31 database checks and #103's 33 calculator
checks remain evidence for their original revisions, not end-to-end acceptance.
The owner requested development continuation, not production deployment.

Five files: provider adapter, focused tests, hosted workflow, this handoff, and
four added lines in the existing signature-verified Stripe webhook handler.
Original webhook file was reconstructed from connector-read exact source and
verified against blob `f580009bd74853840cdebedca5a25216e1a36bdc` before editing.
Existing checkout and payment-success code is otherwise unchanged. No model,
migration, setting, refund policy, frontend file or original record service is edited.
No production credentials or customer records enter this branch or test evidence.

## Implemented provider boundary

- All provider reads/creation use the configured server key explicitly, with matching
  test/live mode checks. Default integration and dispatch switches are absent/False;
  enabling one does not enable the other. No setting/effective date is supplied.
- Read settled GBP PaymentIntent and associated captured Charge. Match identity,
  currency, capture, mode and dispute facts. Connect transfer/application-fee cases
  fail closed pending separately reviewed recovery rules.
- Read every refund page up to a bounded 1,000 entries. Never assume the ten embedded
  Charge refunds are complete. Reject duplicate/malformed/incomplete histories and
  changes between two payment reads. Pending/required-action refunds block a new claim.
- Feed those authenticated observations to the existing durable dispatch claim.
  Only the winning claim can call Refund.create, with its exact pence, operation
  metadata and stable idempotency key. No arbitrary browser amount, reason, timestamp,
  provider response or policy ID is accepted by this adapter.
- A timeout, malformed response or failed persistence after the claim holds the
  operation for reconciliation. It never resets to prepared or creates a fresh key.
  A valid webhook that wins the lost-response race is not overwritten by the hold.
- Reconciliation reads an existing provider refund by stored ID or an exactly unique
  operation metadata match. An empty list is NOT proof a timed-out create failed;
  it does not authorise a second payment. Duplicate matches require review.
- The existing webhook signature check precedes refund-event handling. Signed
  refund.created/updated/failed events locate managed operations; a current provider
  GET supplies status rather than trusting an older event payload. Wrong-mode/account,
  identity and unreadable matched records are non-success responses. Unmanaged
  external refunds are not adopted or attached to a local operation.
- Pending/failed/requires-action/canceled remain distinct. A current provider result
  conflicting with a previously terminal local result sets a sticky reconciliation
  hold, rather than leaving misleading success or silently reversing accounting.
  No ledger/customer-email side effects are performed in this slice.

## Focused checks

28 new test methods use actual PostgreSQL records/services and the existing webhook
signature verifier, with synthetic signed payloads and mocked Stripe SDK methods.
The existing fixture helpers and non-loopback network guard are reused; their
previous test methods are not inherited/repeated. Coverage includes partial explicit
amount, committed stable claim, two simultaneous dispatch callers, timeout recovery,
webhook/timeout race, older notification replay, pending/failed outcomes, unknown
external refunds, wrong mode/currency/amount/identity, pagination/limits, disputed or
changed balances, disabled defaults, and preservation of existing payment-event dispatch.

Local AST/compile, YAML and embedded Bash syntax checks pass. The local runtime lacks
Django/PostgreSQL and cannot reach GitHub directly; hosted execution is the database
runtime evidence. Read the actual final hosted log before claiming pass. No real
Stripe test/live charge, refund, email, n8n action, VPS command or data mutation occurs.

## Still required before enabling anything

1. **Atomic journey cancellation and authorised review.** Wire the existing passenger
   route through one service that prevents assignment/start races and durably stops
   the journey before issuing money. The inherited claim currently expects pending/
   accepted status. Its coordinated cancellation transition must be designed/tested;
   this adapter is NOT yet called by a passenger route, task or admin action.
   Do not enable dispatch or checkout policy independently.
2. **Accounting and operational recovery.** Complete once-only ledger posting,
   authenticated staff review, external/late-failed refund reconciliation, extra
   adjustments and immutable audit history. A terminal-status conflict is currently
   a held outcome, not an automatically resolved bank return. No claim of complete
   financial reconciliation or end-to-end duplicate protection is made.
3. **One refund authority.** External Dashboard refunds and the old live handler are
   not serialized by a local database lock. Two provider reads detect visible changes
   but cannot provide an atomic snapshot with an external dashboard. The final rollout
   must retire competing creation paths and define reconciliation/operational ownership.
   Stripe's captured-amount cap alone does not enforce ACT's lower assessed entitlement.
   Non-card/bank-debit methods and potential disputes need their method-specific review.
4. **Public release alignment.** Matching terms, locale hashes, browser acknowledgement,
   customer/admin wording, physical-browser acceptance and separate exact-revision
   approval remain open. Existing bookings retain their accepted terms. Any actual
   webhook event subscription is an independently approved live configuration change;
   this code does not register/modify one. Automation issue #2 remains the ownership
   notice, not proof of acknowledgement. No native-app changes.

## Primary technical references checked on 25 October 2026

- https://docs.stripe.com/refunds - partial refunds, pending/failure and bank-return states.
- https://docs.stripe.com/api/refunds/list - pagination and payment_intent filter.
- https://docs.stripe.com/api/refunds/object - amount/payment/currency/status fields.
- https://docs.stripe.com/api/charges/object - capture/refund/dispute facts.
- https://docs.stripe.com/api/idempotent_requests - key reuse and pruning after >=24h.
- https://docs.stripe.com/webhooks - raw-body signatures and duplicate/out-of-order events.

These sources explain provider constraints, not ACT's operational readiness. Keep
issue #99 open. Previous supported-framework/security concerns remain recorded; no
silent dependency upgrade is included. This backend branch's frontend subtree must
not be deployed as the website UI candidate.
