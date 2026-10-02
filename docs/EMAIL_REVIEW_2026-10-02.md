# Booking and cancellation email review

Owner approved deployment on 2 October 2026, then supplied a historical booking email PDF and a cancellation/driver-details mockup. These are reference examples, not evidence of the current candidate's live output. No customer data from them is copied here.

- Booking example has the ACT header/footer branding, journey and passenger details, download link, support contacts and management links. Preserve the existing English design in this release; do not introduce an unrelated redesign.
- Cancellation mockup's vague refund timing is superseded by the candidate's approved wording: initiate a confirmed refund to the original method within five working days of confirming its amount; provider posting may take longer.
- The mockup contains visibly garbled headings and a driver-photo/phone overlap. These belong to the supplied PDF; do not treat them as proof that the current HTML email is broken.
- The Arabic email helper did not pass a logo URL to the shared template. It now passes the same existing public ACT logo asset used by English emails. PDF logo handling stays unchanged. HTML alt text remains available if a mail client blocks images.
- The email dispatch regression now asserts the logo URL as well as RTL and Arabic links. Five offline tests pass; no real email was sent.
- Arabic emails use the compact translated template, not a pixel-identical copy of the illustrated English marketing layout. Existing English charity/social/app content is not redesigned in this focused release.

Deployment remains approved. Backend workflow dispatch is not exposed by the connected GitHub tools; browser fallback requires confirmation under the browser-access instructions. Do not claim deployment or live font/PDF/email acceptance until the existing deployment path and bounded checks complete.
