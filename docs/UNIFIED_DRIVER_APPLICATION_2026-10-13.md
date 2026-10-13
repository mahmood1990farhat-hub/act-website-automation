# ACT — Unified Driver Application (website first)

**Status:** Requirements and implementation contract prepared on a draft GitHub branch, **not yet implemented or deployed**. Owner supplied the unified-form requirement on 13 October 2026. This replaces the *new-applicant two-stage submission experience*, **not** the admin approval process. Existing approved drivers, pending legacy applications, driver profile editor, Trip #34 and published n8n Driver v2 remain untouched.

**Source-of-truth review:** website/backend `main` at `1578f33501c3a9894d4d1ff33e165bb4014c7c8f` (not the deployed backend), plus `act-ai-workflows` main `578092bff80afad2eaf4f5174f7d69561043a606`. Main website still has `DriverOnboardingStep1.tsx`, `CreateCaptainAccount.tsx`, `DriverOnboardingRequest`, the authenticated `/api/drivers/onboarding/step2/`, and the admin final-review action. PRs #88–#90 and scoped production releases concern *editing existing drivers*, not this new applicant workflow. GitHub code is not proof of an already deployed unified form.

## Outcome

```text
Public ACT website → One application form (4 labelled sections, ONE submit)
→ Server validates applicant, eligibility and each necessary document
→ Atomic new user + existing onboarding request + private document references
→ Status PENDING_VERIFICATION (never immediately an eligible driver)
→ Welcome email with expiring one-time SET PASSWORD link
→ Applicant sets password → pending-status driver portal access only
→ Authorized ACT admin verifies records/documents and approves, requests corrections, or rejects
→ Only an approved eligible driver may receive/accept trip offers
```

**Retain every already-submitted legacy application and existing two-stage endpoints** until an explicit reviewed migration/cutover. The new route must not try to resubmit, reset or recreate those accounts. New drivers do not upload documents again merely because they finished the initial form. Admin can still request *specific corrected documents*.

## Single applicant-facing form

Use one accessible, mobile-first form with labelled, collapsible/progressive sections. Sections can have Next/Back and auto-saved client draft if appropriate, but do **not** submit Stage 1 for admin approval and return later for Stage 2. Keep the submit button disabled while processing, preserve user-entered data after validation failure, provide clear consent before sending private documents and show a single application reference on success.

| Section | Data | Validation / contract |
| --- | --- | --- |
| 1. Personal | First and last name, DOB, UK mobile, email, residential address / postcode (Google Places with manual fallback) | All required; business policy age **21+** at submission; normalized case-insensitive unique email; E.164 `+44` validation; address string + selected postcode; never trust client-side validation alone |
| 2. TfL / driver | Real TfL PHV driver licence/badge number, expiry, years driving experience; **front/back** of badge and DVLA licence | Required; future licence expiry; individual file max **10 MB**; PDF/JPEG/PNG only, validated server-side by actual file signature/image decoder; record uploaded document types distinctly. Existing `BaseDriver.pco_licence_number` is the passenger-disclosure destination after approval |
| 3. Vehicle | Make, model, year, ACT class, vehicle ownership status, MOT expiry, pets preference; MOT certificate, valid insurance certificate, V5C | **Conditional** on having a registered vehicle; see matrix below. Preserve actual VRM, vehicle **colour**, PHV vehicle licence/document, driver photo and relevant insurance validity required by ACT's existing assignment/passenger-disclosure rules. The public class selector maps to existing **Comfort, Comfort XL, Executive, Executive XL, First** rather than introducing incompatible type IDs |
| 4. Submission | Applicant declarations, truthful-document confirmation, privacy acknowledgement, terms, and **Submit Application** | Explicit policy acceptance; show pending-verification acknowledgment and no guarantee of acceptance. Do **not** collect a password in this form |

### Vehicle ownership condition matrix

| Ownership | Required when submitting | Review outcome |
| --- | --- | --- |
| Own licensed vehicle | Make/model/year, ACT class, VRM, colour, MOT expiry/certificate, valid insurance, V5C, PHV vehicle licence, driver photo | Can enter standard admin verification queue if complete |
| Hiring a licensed vehicle | Make/model/year, ACT class, VRM, colour, MOT, valid insurance, PHV vehicle licence, hire/right-to-use evidence, driver photo; request V5C only if reasonably available | Can enter verification queue when sufficient proof of lawful use is provided |
| No vehicle yet | Personal and TfL/DVLA identity proof only; no invented vehicle values or placeholders | Record as **AWAITING_VEHICLE** (application accepted, driver **not dispatch eligible**). Admin may help source vehicle; do not approve for trips until completed evidence |
| Other | Request explanation and relevant ownership/authority evidence, with same dispatch-eligibility proof as applicable | Admin verifies before any final approval |

**Do not treat a lack of vehicle as a validation error** when the user selected `Don't have a vehicle`; equally do not mark such a driver profile complete or assign trips.

## Backend / data changes (implementation requirements)

- Reuse `CustomUser` and `DriverOnboardingRequest` as the authoritative application identity and review records. Introduce only **additive, backward-compatible fields/migrations** for DOB, expiry dates, vehicle proof, pets, driver photograph and consolidated submission metadata that do not already exist. Preserve the seven legacy statuses and associated admin actions; add a clearly marked unified submission status/flag (and `awaiting_vehicle`) with compatible admin filtering. Do not silently set stage-1-approved or `final_approved`.
- New `POST /api/drivers/onboarding/apply/` accepts **one multipart payload** and validates all conditional requirements *before* persisting the application. Process in a database transaction, enforce unique normalized email under concurrency, and ensure rejected validation does not leave a partially created driver/user. Never return raw document bytes in the response.
- Applicant user record starts with **unusable password**, driver account type, `is_admin_verified=False`, `is_profile_completed=False`, `is_active=False`; applicant activates portal-only login after redeeming the emailed set-password link, but *remains unverified*. Driver offering/acceptance must continue to require existing verification and vehicle/identity gates. The password is never emailed or logged.
- Use an expiring **single-use token** (24-hour target), verified server-side; after successful password setup, invalidate the token and allow login to onboarding status, not to driving jobs. Add guarded resend/recovery without duplicate application or account. Design for email-send failures using a retryable marker/queue rather than an orphan account or a duplicate welcome email.
- Document attachments must be **private**: no public, guessable `/media/` URLs for badge, DVLA, V5C, insurance, DOB or photos. Add an authorized admin review/download mechanism, strong file content/type validation, size limits, retention/deletion controls and data-minimal logs. Do not email actual identity documents or write secrets into GitHub/CI logs. This is a release blocker, not optional polish.
- The existing `NormalDriver` / `BaseDriver` registration and vehicle creation can be reused when the application has a verified, permitted vehicle and appropriate docs; **do not create the same driver twice** or auto-verify at submission. Ensure the existing admin details, trip assignment, licence/photo, make/model/colour and vehicle class remain consistent.
- Preserve existing `/onboarding/step1/`, `/onboarding/step2/`, `/onboarding/status/`, final-review and modification interfaces for old applications until an explicit compatibility gate passes. Redirect *new applicants only* to the new unified form upon accepted cutover.
- Protect submission with suitable server throttling, validation, duplicate detection, no sensitive exception logging and durable private file handling. Send all emails from ACT verified domain; customer-facing English/Arabic and accessible responsive behaviour at minimum; preserve existing live website/bookings.

## n8n and operation coordination

- The **Website & Mobile Apps** workstream owns the one-form website, Django API, password setup and admin acceptance.
- **ACT AI Automation V2** owns n8n/agents. The Driver Recruitment & Coverage Agent v2 has existing published/read-back evidence; **do not clone, edit or republish it** as part of this website change.
- After the unified backend event is implemented, agree a **single idempotent event contract** (application ID, schema version, `submission_mode=unified`, lifecycle state, UTC timestamp; no PII or file content). Map it to the existing onboarding/driver coverage handling in the automation workstream, avoiding double admin/welcome notifications. The latest inspected website `main` did not expose a supported n8n publisher module: verify the deployed/connected contract before relying on it.
- Driver availability/class and coverage agent projections must not treat unapproved applicants, missing-vehicle candidates or uploaded documents as available drivers.

## Acceptance gates — one finite, non-repetitive suite

1. **UI:** A single mobile and desktop application submits once; browser and server validate fields/conditional vehicle rules; Google Places and manual fallback work; one application success reference.
2. **Data:** One pending account and linked application with genuine uploaded documents; failed validation/duplicate email does not create a second record; legacy applicants/accounts untouched.
3. **Password:** One welcome/set-password email; token expires, cannot be replayed, and invalid tokens reveal no private records; login reaches pending status only.
4. **Admin and compliance:** Authorized admin can securely review identity/vehicle evidence, approve/reject/request corrections, including no-vehicle pending path; unauthorized requests cannot read/download docs.
5. **Dispatch isolation:** Before final approval no offers, assignments or access to trip actions; after approval driver photo/licence/VRM/make/model/colour and correct vehicle class satisfy existing checks.
6. **n8n coordination:** If/when enabled, one lifecycle event per transition with redaction/idempotency and no duplicate emails; existing published Driver v2 unaffected.
7. **Release:** Django migration plan + verified backup review; branch tests and frontend build; isolated browser/API/email acceptance. Owner approval before any production migrations, deployment, automatic job or app changes. Do not touch paid Trip #34 or run fresh Stripe/Celery tests without a related change.

## Explicit outstanding design / approval gates

- Confirm private document storage access/retention and expiry semantics before implementing live uploads.
- Confirm which hired-vehicle evidence replaces V5C where the applicant does not own the vehicle.
- Ensure existing admin final-review action cannot accidentally approve vehicle-less applicants; design is intentionally fail-closed.
- Release new application route independently of existing driver profile correction and the unresolved full booking-to-completed-journey website acceptance.

**State separation:** This document is an agreed *implementation proposal drafted in GitHub*; no code, tests, migration, merge or live rollout is implied by the document alone.
