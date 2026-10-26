# Checkout terms discovery — public read contract, no publication

## Preserved baseline and scope
Base backend: PR #109 `3917049d6437d67e4fd29210c56cb855a1a0c28e`.
Frontend remains the separate PR #110 `fb93e5534de15e25e3b45f1935f6a61b25c672e8`.
Policy review remains PR #101 `5618d56e111510e7cd1e32ecf524f67c34bcd9b7`.
Their latest refs/status and completed test evidence were inspected first. Do not
use this backend branch's frontend subtree as a website release.

The accepted customer direction remains >24h full, >12h through exactly24h 50%,
<=12h standard zero, with the accepted fair-loss safeguard and no retrospective
reassignment of older contracts. No cancellation calculation, payment execution,
existing booking/cancellation email, PDF generator or template is changed here.
No effective date, reviewed release configuration, public PDF or translated legal
text is created, published or activated by this patch.

## Concrete gap addressed
The backend already requires an exact acknowledgement before creating a payment.
The browser previously had no public endpoint for the corresponding reviewed text,
version, hash and PDF link. The existing ConfirmFlightDetails component initiates
payment at its confirmation step; the later CheckoutForm checkbox alone cannot
satisfy a requirement to save terms BEFORE payment initiation. Those components
were read; they are NOT modified or claimed integrated by this backend-only patch.

`GET /api/payments/checkout-terms/?locale=en` exposes only the public fields:
`schema`, `enabled`, `terms_version`, `terms_sha256`, `locale`, `text`,
`document_url`, `pdf_sha256`, `effective_at`.
The URL is relative to the PUBLIC WEBSITE, not an arbitrary provider-controlled
host. Viewing is not agreement, creates no record and has no financial side effect.
The new route requires no passenger login or payment identifier, so guest checkout
can read the same public document. Existing private operator routes stay protected.

The existing literal-boolean `ACT_BOOKING_TERMS_CHECKOUT_ENABLED` controls discovery.
When false/absent, the result is only `{schema:1,enabled:false}`; no draft leaks.
When enabled, only a published, effective, supported-policy release with an exact
reviewed locale is returned. Text SHA-256 is verified. Malformed dates, document
hashes, local PDF paths, versions or locale data return a safe 503 without details.
Unsupported, missing, duplicate or additional query parameters return 400. Requests
other than GET return 405. Every outcome is non-cacheable. There is no English
fallback masquerading as a translation and no exposure of arbitrary internal keys.

The capture service is NOT refactored. It independently revalidates the same
server-selected release before payment and remains the authority. Tests check
that the discovered fields produce its existing exact acknowledgement format:
`{accepted:true,terms_version,terms_sha256,locale}`. A changed release or false
acknowledgement is rejected without creating an acceptance record.

## Important verification limits
The PDF hash is checked for format, not fetched. It is an assertion supplied by
the reviewed release; final publication MUST compare the actual generated/served
PDF bytes and translated sources with that hash. This endpoint does not prove
legal approval, successful PDF hosting, link availability or that someone read it.

This is the read contract, not the final browser integration. The next frontend
change must show the exact text and matching PDF before payment initiation, start
with an unchecked deliberate acknowledgement, and send only the four permitted
fields to both guest and registered initiation paths. Never put acceptance in
local/session storage as reusable blanket consent. Reset it for material booking,
language or release changes. Refresh the descriptor before initiation; on mismatch
require review again and never auto-retry payment. Endpoint errors are not legacy
mode. The existing backend remains the last check against stale/forged inputs.

At final card payment, show the SAME accepted document, not the old dictionary
terms or a newly fetched release. Preserve existing customer privacy controls;
terms acceptance is not marketing consent. Keep all new behaviour disabled until
the coordinated frontend/backend/documents/refund release is explicitly approved.

## Focused checks
New suite: 13 read-contract tests plus 3 PostgreSQL capture-compatibility tests.
Checks strict gates, absence of draft leakage, field allowlist, non-cacheability,
locale/query/method validation, future/malformed releases, text/PDF paths/hashes,
verbatim synthetic translation, JSON safety, actual capture parity and rejection
of a stale/unchecked acknowledgement. Fixture helpers are reused, not old tests.
No real public document, payment, refund, email, PDF render or customer data is used.
Outbound connections are blocked during tests. The read-only tests prohibit DB
queries; the three capture tests use a disposable PostgreSQL database only.

Local AST and two-line URL-change preservation check passed. Hosted runtime result
is pending at commit time and must be recorded from actual completed evidence.
No prior completed financial, browser, build or email/PDF suite is rerun here.

## Release holds
The UI connection described above, dedicated driver-policy link/PDF integration,
company/privacy/fairness facts, legal-document publication/locale hashes, support
exception resolution, combined build and desktop/physical-mobile acceptance remain
open in #99. This does not invent a deadline or enable a new cancellation policy.
Existing framework-support/security risk stays recorded, not silently upgraded.
No merge, deployment, production migration/configuration, permission grant, live
financial operation, email replay, n8n change or native-app operation is authorised.
