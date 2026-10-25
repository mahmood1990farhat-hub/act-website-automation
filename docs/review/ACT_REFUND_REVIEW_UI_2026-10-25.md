# Existing dashboard: cancellation and refund review

Frontend base: PR #100, 98fc47172c2054e2a059506a6cef717e5b8f3dcf.
Backend companion: PR #109, 3917049d6437d67e4fd29210c56cb855a1a0c28e,
based on #108. These are separate exact frontend/backend candidates: do NOT
publish the older opposite subtree from either branch. No production change.

The new /{locale}/dashboard/cancellations page reuses the existing dashboard
layout and admin login. A link is added above the existing Trips page. No sidebar
redesign or second admin system. Internal screen text remains English. Existing
booking/cancellation email and PDF sources are untouched.

Queue: fixed-page case list, exact trip ID search, empty/error/permission states.
Detail: original accepted terms, first receipt, stopped time, captured amount,
provider operation and accounting states. Unknown historical terms remain unknown.
No current-policy default, browser refund calculator, bank-credit assertion or
customer document data. Times display in Europe/London; amounts are GBP pence.

Existing Bearer token and configured API base are reused. Narrow fetch wrapper
uses no-store, no browser persistence, bounded timeouts and NO automatic retries.
GET refreshes stored ACT state only. Explicit reconciliation POST uses the existing
endpoint and cannot create another refund, but can update local accounting state.
Review POST sends only reviewed_net_loss_pence and review_reference to the existing
server action. Loss is converted from a validated decimal string without float
rounding. Missing/negative/scientific notation is not silently accepted.

Review requires input validation, an inspection step and a separate unchecked
confirmation acknowledgement. A synchronous in-flight guard prevents rapid double
POSTs. A failed/uncertain POST is not automatically replayed; the open case becomes
read-only until the operator investigates/refetches/reopens it. This UI does not
replace backend locking, permission checks or immutable operation identity.
Late detail GET responses cannot overwrite a newly selected case. Permission
errors clear sensitive case details. Server action availability is advisory; the
backend remains authoritative if state/permissions change after viewing.

16 focused browser checks (8 desktop Chromium / 8 emulated mobile WebKit) use the
ACT component compiled by esbuild, its scoped styles, a local HTTP harness and
mocked same-origin API responses. Off-origin requests are blocked. They cover
search/read-only entry, HTML escaping, validation, explicit acknowledgement,
double click, pending/success display, reconciliation payload, uncertain requests,
unknown terms, permissions, stale responses, empty state and responsive overflow.
Type-generation/full TypeScript checks verify compatibility with the existing app.
Hosted evidence must be read before claiming a pass. This is not physical iPhone,
whole dashboard/browser-backend end-to-end testing or a production build artifact.
Original driver form, payment, email and PDF suites are not repeated.

No automatic grant of staff permissions, new Stripe session, production settings,
policy publication, API purchase, migration, n8n, native-app work, merge or deployment.
Backend event/outcome ownership remains as recorded in act-ai-workflows issue #2.
Remaining coordinated policy/checkout release, exception-resolution workflow,
combined acceptance and exact-release approval remain open in issue #99.

React effect cleanup reference: https://react.dev/reference/react/useEffect .
