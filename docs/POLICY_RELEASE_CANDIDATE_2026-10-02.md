# ACT policy release candidate — 2 October 2026

Status: prepared for content review; NOT deployed and NOT yet ready for final deployment approval.

## Scope
Based on production main 29de5e0cf4f3a1d3d12944e0b435d0cd7a0476ea.
Branch: codex/policy-release-20261002.
Six runtime files only: English/Arabic home dictionaries; passenger booking and cancellation email templates; cancellation plain-text email; booking/cancellation PDF generator copy.
French foundation, payment calculations, refund execution, database models, workflows and deployment configuration are excluded.

## Completed
- Master Operations Document version 1.2 records owner-approved nine-clause policy and publication-pending status. Existing file updated, not duplicated.
- English and Arabic terms fallback, flight FAQ, cancellation FAQ and payment notice use the approved policy.
- Booking confirmation email/PDF explains cancellation/amendment contact and receipt-time rule.
- Cancellation HTML/plain-text email and PDF state original payment method, initiation within five working days after amount confirmation, and bank timing.
- Confirmation wording preserves the terms agreed when booked; existing stored PDFs are not regenerated.
- One-page policy review PDF prepared. This contains cancellation clauses only, not replacement full terms.
- Approved French copy remains on the unpublished language foundation branch.

## Remaining release gate
1. Obtain current managed TERMS_AND_CONDITIONS PDF and any FAQ PDF, preserve unrelated provisions, replace conflicting cancellation/refund/flight wording, and prepare full replacement files. Dictionary updates alone may be hidden by a managed PDF.
   Source: Terms.tsx uses getInstructionFile; InstructionFile data is managed outside GitHub.
   This session public site retrieval returned HTTP 403; web retrieval did not provide the current PDF. No live document was modified.
2. Decide and record activation time for new bookings. Do not apply new cancellation deductions retrospectively.
3. Owner reviews the complete package and approves deployment only once the managed documents are included.

## Operational finding — no payment change in this release
CancelTripView currently accepts only pending trips and requests a full Stripe refund for paid bookings with a payment intent, without a 24-hour calculation. This candidate leaves that behaviour unchanged. It does not implement loss-based deductions or a refund review queue. Accepted bookings and other cancellations need the existing contact/admin process; do not advertise automatic enforcement. A full refund can be more generous than the policy's permitted deduction, but loss-based handling is not implemented.

## Validation
- English/Arabic JSON parsed; reverting exactly the terms insertion, two FAQ answers and payment subtitle restores the production-main dictionaries byte-for-data (no unrelated key/value changes).
- Changed Python source parsed with ast; no imports or calls to Stripe, email sending or production database during validation.
- All 13 master-document pages and the one-page policy PDF rendered and visually inspected.
- Django is unavailable in this local runtime; template rendering and integrated booking/PDF tests have NOT been claimed.
- No production booking, email, cancellation or refund executed.

## Release and rollback after approval
- Preserve current managed PDF files and versions first.
- Coordinate replacement managed documents with the approved effective time and website publication.
- Main merge automatically deploys frontend. Backend requires separate manual exact-SHA workflow dispatch; merge alone does not deploy email/PDF changes.
- Run one bounded read-only English/Arabic terms/FAQ/checkout review plus local synthetic email/PDF render before backend dispatch. Do not perform real customer transactions.
- If publication fails, restore previous files and revert only this candidate's changes. Preserve booking-specific accepted terms and communications.
