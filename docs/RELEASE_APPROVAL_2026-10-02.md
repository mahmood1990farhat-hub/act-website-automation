# English/Arabic policy and booking release — approval review

Status: prepared for owner deployment approval; NOT deployed. French remains hidden.
Candidate branch: `codex/policy-release-20261002`.
Production main checked: `29de5e0cf4f3a1d3d12944e0b435d0cd7a0476ea`.

## Completed scope
- Approved English/Arabic cancellation and refund copy in terms, FAQs, payment notice and customer documents.
- Remaining booking-screen display text translated: passenger details/country labels, passenger counts, child/infant seat options, flight details and timing guidance, review and confirmation screens. Canonical form values and customer input remain unchanged.
- Arabic AM/PM display; Stripe Elements receives the selected en/ar locale; Arabic payment-failure fallback. Third-party authentication pages remain provider-controlled.
- Corrected the remaining vehicle-selection one-hour cancellation claim to a full refund with at least 24 hours' notice; review screen wording now explicitly includes exactly 24 hours.
- Confirmation's My Trips link follows route locale, with Arabic next-step information and RTL direction.
- Booking-owned language persisted through pending payment, webhook transfer and trip updates, then used by five customer email paths and booking/cancellation PDFs.
- Previously reviewed Arabic booking/cancellation PDFs retain the official ACT logo at top left. Existing stored customer PDFs are not regenerated.
- Fixed the English driver-detail email's split registration variable; added regression coverage.

## Focused verification
- Production Next.js build passed, including TypeScript and page generation. Existing middleware deprecation warning only; no new build blocker.
- Offline React rendering checked English/Arabic passenger, child-seat and flight screens, RTL, preserved country/seat values and customer data.
- Flight-guidance checks cover valid windows, invalid input and midnight rollover without changing calculations.
- Static JSX scan passed for the seven reviewed booking screens; dynamic provider/customer/catalogue text is not covered by this scan.
- Five backend offline tests passed, covering saved-language dispatch, legacy English fallback, escaping/refund messages and English registration rendering. No database, outgoing messages, payment or real booking used.
- Earlier synthetic English/Arabic PDF render and visual review are recorded in the booking-language checkpoint. This pass does not claim a live end-to-end booking test.

## Release boundary and remaining checks
- Approve frontend AND backend deployment explicitly. Main triggers frontend deployment; backend requires separate exact-SHA workflow dispatch, with migrations disabled.
- Confirm Arabic font availability and perform one synthetic Arabic PDF render on the deployment environment before declaring backend PDF acceptance. Local rendering alone does not prove server font availability.
- Record the policy effective publication time for new bookings. Preserve previously agreed terms; no retrospective deductions.
- During release, check the actual live English/Arabic terms/FAQ source and perform a bounded read-only booking-screen review. If an active managed terms PDF appears, align that file before publication.
- Stripe-issued receipts, external authentication screens and arbitrary backend/provider error text are not guaranteed to follow booking language by this change. No Stripe-account access or receipt configuration was changed.
- Full database/webhook integration and real payment/refund testing were not run. No automated loss-based refund deductions added: existing pending-trip full-refund behaviour remains, with the existing contact/admin process for other cases.
- French and the other proposed languages are not released. No SEO, n8n or unrelated infrastructure work included.

## Approval decision and next task
Approve this focused English/Arabic release, then deploy the reviewed commit through the existing frontend and backend paths and complete the bounded live/font/PDF checks above. Stop if those checks fail; do not claim language-complete production acceptance or run real customer transactions.

Rollback: record the preceding frontend/backend deployed SHAs, revert only this release's changes if necessary, and keep historical booking terms and stored documents intact.
