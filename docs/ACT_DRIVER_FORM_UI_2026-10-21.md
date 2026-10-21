# ACT issue #99: shared driver-application UI correction

Base: deployed frontend `892317fcf938fad5fa6cd9a833a79e900dcc4d8f`.
Compatible backend remains `82c0b14ad2a71e1ce3d8d1df3527431b698ac461`.
This is a separate frontend-only review candidate. Do not deploy the backend
subtree from this frontend branch. Do not merge, deploy, migrate, restart,
resend notifications or touch n8n as part of these tests.

## Implemented in this candidate

- One responsive upload control for identity, photograph, optional DBS and
  vehicle evidence. Clear Upload / Replace / Remove buttons, one filename,
  per-document format/10-MB guidance and precise selected/not-uploaded status.
- The parent component's File objects are used consistently for display,
  validation and FormData. Native inputs are picker-only and never show a
  contradictory native filename. Empty picker results preserve selections;
  explicit Remove clears them. Back/Continue preserves files in memory only.
- Empty, oversized or unsupported files block advancement; driver photographs
  must be JPEG/PNG. Existing backend file-content verification is unchanged.
- Previously shown step errors recompute from current fields and files;
  a corrected selection or completed consent no longer leaves a stale warning.
- Continue and final Submit have distinct keyed controls. Only deliberate
  activation of the final submit control can POST. A synchronous in-flight
  guard prevents rapid duplicate submits; normal backend duplicate controls
  remain intact. The endpoint and multipart field names are unchanged.
- Make and dependent model selectors with an explicit not-listed fallback;
  changing make clears model. Suggestions are not a complete catalogue or a
  statement of vehicle eligibility. Year is current year down to 2015.
- Rental/hire/lease wording reuses hiring_a_phv/hire_agreement. Hidden evidence
  from a prior ownership choice is retained in memory but excluded from the
  current payload. No-vehicle applications continue to exclude vehicle data.
- Clearer DBS timing text: initial application may omit the certificate, but
  ACT requests missing evidence in secure review before final approval for trips.
  This is copy, NOT a new automatic admin workflow or certificate-presence gate.
- Review summary includes personal/licence/vehicle details and selected documents,
  edit buttons, readable ownership labels and mobile-friendly action spacing.

## Validation scope

The new hosted CI is limited to this draft branch, uses the exact committed
frontend lockfile, and has read-only repository permissions. It runs the existing
unified source guard and TypeScript, then 10 focused cases on desktop Chromium
and emulated mobile WebKit (20 browser cases total). Every test uses synthetic
fields and files. The real form runs against local mocked Places and submission
responses; all off-origin requests are blocked. No ACT API, email, payment or
production database is involved. Screenshots contain only synthetic test data.

Browser emulation is not a physical iPhone/Safari picker or toolbar test. Picker
cancellation is simulated as an empty result. A real-device visual review remains
before acceptance. New application files and data are not uploaded to a backend.
Do not reinterpret these UI tests as the earlier full onboarding/backend tests.
Do not rerun the completed production backup, migration or release process.

## Still open in issue #99 — do not close or deploy yet

1. Dedicated driver-application terms and driver-specific privacy revisions,
   owner review, correct links, matching locale source/PDF/hash manifest.
   This patch leaves existing policy links/documents untouched; it does NOT
   cure the recorded passenger-terms/driver-terms mismatch.
2. Vehicle registration auto-fill requires verified permitted provider access
   and model coverage. No lookup/API key/provider cost is introduced here.
3. Email Junk placement needs actual authentication/header evidence; delivery
   and successful password setup must not be repeated or represented as failed.
4. Desktop sign-off, then physical mobile-browser sign-off, with no duplicate
   production application or actual driver approval. Native apps remain deferred.
5. Separate exact-revision production approval after the remaining review.

No screenshot PII, password-setup tokens, credentials or original document
filenames are included in this public development record.

## References used for the implementation

- React state preservation and keyed identity:
  https://react.dev/learn/preserving-and-resetting-state
- Browser file picker and selection semantics:
  https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file
- Playwright file-input testing and emulation:
  https://playwright.dev/docs/input
  https://playwright.dev/docs/emulation
