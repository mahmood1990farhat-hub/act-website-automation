# Refund review dashboard API — candidate only

Base: PR #108, 5dda7af99f2dafaba8b73cb55b5a9dfce343c767. Latest PRs,
frontend #100 (98fc471), dashboard Trips page and existing read/write APIs were
checked before editing. Existing emails/PDFs and all refund executors are preserved.

This patch adds a paginated read-only cancellation queue and extends GET on the
existing review URL. The review POST is the original inherited method; the
reconciliation POST is unchanged. Both reads require active staff plus the
existing payments.review_cancellationcase permission and return no-store headers.
Opening/refreshing a case NEVER contacts Stripe, changes records or sends email.

Contract: GET /api/payments/cancellations/?page=1[&trip_id=123] returns data[] and
pagination {page,page_size,count,has_next}. Page size is fixed at 20. Rows contain
only case/trip references, first receipt, journey/refund status and hold indicator.
GET /api/payments/cancellations/{uuid}/review/ preserves original keys and adds
operator_schema=1, recorded terms/version/text/hash/language, captured pence,
operation/accounting status and advisory action availability. No contact details,
card data or provider keys/IDs are exposed by the new representation.

A recorded snapshot is not a new effective policy. Unknown/corrupt/differently
accepted terms cannot acquire the new percentages via this screen. GET exposes
saved state, not fresh Stripe status. Existing POST guards remain authoritative;
availability may change between viewing and confirmation. A reviewed amount is
net loss, NOT a browser-selected refund amount. In-flight/held/final operations
cannot be replaced by the review form. Reconciliation can update local accounting,
but the existing endpoint never issues another Refund.create.

No new migration, flag, dependency, money rule, provider call, notification or
public policy is introduced. Paused server flags stay paused. Existing 3-hour
booking lead time is untouched. Safe holds are not resolved exceptions.

14 focused disposable PostgreSQL/DRF tests cover read permissions, pagination,
filters, original POST inheritance, stored-versus-current policy, invalid/unknown
terms, paused actions, pending/final states, no provider/mailer calls, no customer
contact leakage and 404 handling. Actual hosted output must be inspected before
claiming tests passed. Previous calculation/storage/checkout/provider/template
suites are not rerun by this workflow.

Pair with the separate frontend candidate based on 98fc471, NOT this branch's
older frontend subtree. The browser page belongs in the existing dashboard and
must require explicit confirmation for the existing review POST. Coordinated
release, full exception support, policy publication and owner approval remain
outstanding. No production deployment, migration, real refund or email authorised.

Technical references: DRF permissions documentation (official),
https://www.django-rest-framework.org/api-guide/permissions/ .
