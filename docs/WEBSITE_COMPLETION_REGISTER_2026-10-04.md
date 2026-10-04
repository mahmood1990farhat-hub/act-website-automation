# ACT website completion register — 4 October 2026

**Status: initial review and one isolated validation repair. Not website acceptance, not deployed.**

## Agreed order

Finish and accept the website from first visit through a completed journey before extending work on the passenger and driver mobile apps. The apps must subsequently match the accepted website rules and shared backend behaviour. Social media/AI communications and advanced recruitment automation remain later workstreams. Keep driver applications on the existing website form. Essential booking emails, documents and operational notifications are part of website completion, not deferred communications work.

## Baseline and safeguards

- Repository: `mahmood1990farhat-hub/act-website-automation`.
- Main inspected: `a111eb4767951a6c5b76a87cc9ce3e5ec1525337` (merged PR #69, 2 October).
- Pending candidate preserved: draft PR #70, `codex/complete-customer-languages-20261002`, commit `7d5d95052550836876aeba618043e903273920da`, tree `fea464fd5b112a1c660c1086bbfc0e67590570fd`.
- This incremental review/fix is based on that candidate, not a replacement of its language, email or document work. Do not merge this incremental change directly to main as an accidental release of all PR #70 changes.
- `.github/workflows/deploy-frontend.yml` deploys on pushes to main. No main update, deployment, production booking/payment, customer message, OTP, mobile-app change or n8n change was performed in this review.
- Owner has stated there is no separate staging/test site. Do not assume a usable staging service exists because older planning documents mention one. Real-provider testing needs a verified isolated environment with test credentials and controlled delivery. Do not switch the live site's payment keys for these tests.

## Evidence from this review

Read-only public-page inspection covered `/en`, `/en/about-us`, `/en/download-app` and `/en/auth?captain=1` on the live domain. These are page-content/navigation observations, not a visual browser, form-submission, download or authenticated acceptance test. The homepage still contains the legacy label `ATG` and the footer `Airport taxi Transfer Company`; include both in brand cleanup. The About page displays customer-count and star-rating claims that require supporting evidence before sign-off; this review does not establish whether those claims are true or false. The app page describes Android APK installation; availability, downloads and app readiness were not verified.

PR #70 and `docs/SEVEN_LANGUAGE_IMPLEMENTATION_2026-10-03.md` report prior offline translation, PDF, browser and synthetic journey checks. That document explicitly limits the synthetic journey tests to booking review and states real Google/Stripe/Twilio/email and authenticated submissions remain unverified. Those earlier test results were read, **not rerun in this session**. They must not be relabelled as complete end-to-end acceptance.

A local full-repository checkout could not be obtained in this environment because GitHub DNS resolution failed. Connector reads remained available. For the bounded repair below, the fetched production helper was copied locally and its Git blob hash verified against GitHub before testing. No full frontend build or complete backend/browser suite was executed here.

## Repair WEB-001: validate coordinates at the quote payload boundary

Source: `act_website-main/src/components/_components/bookTaxi/quote-request.ts`.

Original blob verified locally: `2a54158ba415295a9feeee707ea8498ef5662c97`.

Finding: the helper accepted finite coordinates outside latitude/longitude limits and did not independently validate added stop coordinates. `RoutePoints.tsx` already checks selected route points in the UI, so this is payload-boundary hardening and a source-level reproduced gap, not evidence that a live customer completed an invalid journey.

Change: enforce latitude [-90, 90] and longitude [-180, 180], preserve the existing (0,0) sentinel rejection, and validate every added stop before constructing the payload. Preserve normal quote fields, stop order, single-zero coordinate support, date padding, passenger/luggage values and meet-and-greet option. No fare formula, service-area policy, booking lead time, date/time semantics or payment behaviour was changed. Geographic coordinate validity is not a service-area eligibility check.

New test: `act_website-main/tests/check-quote-coordinate-validation.cjs`.

| Verification performed here | Result |
| --- | --- |
| New 33-case suite against exact original helper | 17 pass, 16 fail |
| Same suite against revised helper | 33 pass, 0 fail |
| Strict TypeScript check of this helper only | Pass |
| Full application build, UI regression, backend integration, providers | Not run |

Reproduce from `act_website-main` with project dev dependencies installed:

```sh
node --test tests/check-quote-coordinate-validation.cjs
npx tsc --noEmit --strict --skipLibCheck --target ES2020 --module commonjs src/components/_components/bookTaxi/quote-request.ts
```

These are isolated helper tests using synthetic coordinates. Passing them does not certify the booking journey or backend input validation. Backend coordinate/stop validation remains an independent acceptance requirement.

## Website acceptance matrix

All unchecked rows remain open. A feature existing in source is not sufficient to mark it accepted. Attach candidate SHA, environment, scenario, expected/actual result and evidence for every completed row. Treat failed, blocked and untested as different statuses.

| ID | Area | Required acceptance evidence | Current position |
| --- | --- | --- | --- |
| WEB-002 | Brand and public pages | Consistent ACT name/contact details; evidence-backed claims; functioning navigation/airport pages; desktop/mobile visual review | Partial read-only inspection; cleanup identified |
| WEB-003 | Accessibility and mobile use | Keyboard/focus, input labels, readable errors, small screens, touch controls, loading/empty/error states | Not verified |
| WEB-004 | Route entry | Valid address selection, stale selection reset, pickup/drop-off swap, airport direction/terminal, valid/missing/removed stops, approved service-area boundaries | Coordinate helper repaired; UI/provider checks open |
| WEB-005 | Date and time | Approved booking lead-time rules; past/invalid input; midnight; UK daylight-saving changes; customers booking from other time zones | Not verified |
| WEB-006 | Passengers and luggage | Adults/children/infants, child-seat choices, integer/nonnegative counts, vehicle capacities and no-vehicle outcome | Not verified end to end |
| WEB-007 | Quote and price | Backend-authoritative tariff, minimum fare, uplift, airport fees and options; rounding; route/vehicle changes invalidate stale quote; prior distance-band anomaly regression | Not verified end to end; no tariff changed |
| WEB-008 | Guest booking | Guest contact details retained through payment, trip record, confirmations and support; no unwanted account requirement | Not verified end to end |
| WEB-009 | Accounts | Passenger signup/login/logout, reset/verification, profile updates and guest/account boundaries | Not verified with real test backend |
| WEB-010 | Review and navigation | All entered facts match review; edit/back/refresh/language-switch handling; selected language persists; no stale price/payment state | Prior PR #70 bounded evidence only |
| WEB-011 | Payment outcomes | Stripe test-mode success, decline, authentication challenge/cancel, pending/unknown outcome, redirect/refresh/retry and double-click protection; Clearpay only under its approved release scope | No payment executed here |
| WEB-012 | Payment-to-booking consistency | Authentic webhook; duplicate/out-of-order delivery; exact amount/currency; one intended booking/payment; retry/reconciliation; UI confirmation reflects persisted state | Not verified end to end |
| WEB-013 | Confirmations and documents | Correct booking facts/language; preserved English styling and clickable images/text; correct booking-owned PDF links and access; no duplicate messages | Prior PR #70 offline evidence only; delivery/access open |
| WEB-014 | Admin and assignment | Paid/guest bookings visible once; correct facts; authorised driver assignment, acceptance/rejection/reassignment, conflict handling | Not verified end to end |
| WEB-015 | Driver website journey | Approved test driver sees correct job; valid journey-state sequence through completion; authorised access and disconnect handling | Not verified; no mobile-app development required for this gate |
| WEB-016 | Passenger operational updates | Correct driver/vehicle details and scheduled messages; tracking where supported; late assignment, cancellation and rescheduling behaviour | Not verified end to end |
| WEB-017 | Completion and history | Completed state agrees across passenger, driver and admin; correct receipt/history and earnings records; no duplicate settlement | Not verified end to end |
| WEB-018 | Cancellation/refunds | Approved policy thresholds, passenger/driver cancellation, refund accounting and notices; replays cannot duplicate a refund | Not verified; no real refund authorised |
| WEB-019 | Support and contact | Contact, complaint and lost-property forms; attachments; validation; ownership checks; confirmation and staff visibility | Page content inspected only |
| WEB-020 | Driver applications | Website application through verification, documents/re-upload and controlled approval; one driver identity; clear errors | Entry page inspected only |
| WEB-021 | Security and privacy | Backend permissions, guest/authenticated record and PDF isolation, secrets, uploads, rate limits, appropriate logs/retention | Separate review still required |
| WEB-022 | Release and recovery | Exact frontend/backend versions, migrations, scheduler/services, monitoring, backups/restore/rollback and smoke checks | Deployment trigger inspected; runtime checks open |
| WEB-023 | Final sign-off | Successful complete synthetic/test-provider journey plus failure journeys, desktop/mobile evidence, owner review, no unresolved release blockers | Not achieved |

## Required complete-journey evidence

Public visit -> route/date/passengers/luggage -> quote/eligible vehicle -> passenger/flight/extra details -> review -> test payment -> verified webhook/persisted booking -> passenger/owner confirmation -> admin assignment -> approved driver acceptance -> scheduled passenger details -> journey-state progression -> completed trip -> matching history/receipt/earnings.

Repeat relevant journeys as guest and signed-in passenger, airport pickup and airport drop-off, city transfer, and supported languages/viewport sizes. Negative scenarios must include decline, authentication interruption, unknown payment result, replay, failed notification, rejected assignment and cancellation. Do not use mock-only evidence to claim real-provider acceptance. Simulated trip completion is not a physical-road journey test; any operational road trial is a separate controlled check.

## Immediate next implementation slice

Review route/date/time/passenger validation and the quote-to-payment handoff against the actual backend endpoints. Extend tests without changing approved tariffs/policies. Prepare isolated backend/test-provider execution and delivery controls before exercising payment, booking creation, staff assignment or customer messages. Do not introduce a paid service or production connection without the necessary approval. Keep PR #70's release conditions and English-template/link preservation intact.

The website is accepted only after the defined evidence and owner review are complete. Mobile-app matching starts after that gate, not after this initial repair.
