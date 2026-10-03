# ACT customer-language completion workstream

**Latest implementation:** [Seven-language implementation and evidence — 3 October](SEVEN_LANGUAGE_IMPLEMENTATION_2026-10-03.md) supersedes the source-code gaps listed below. All seven customer catalogues and matching bundled documents are implemented and tested in the draft; production/provider acceptance and coordinated publication are still unverified. Earlier sections remain historical records.

Started 2 October 2026 after the owner's instruction to prioritise **all five additional languages, including emails and the complete booking journey**. This workstream comes before resuming Gemini/n8n operational handover. Those tasks remain pending; they have not been cancelled.

**Status: second implementation checkpoint; incomplete and unpublished. Not a release candidate or a completed five-language launch.**

## Scope and current position

| Language | Public website | Customer frontend | Booking emails and PDFs in this branch | Welcome/reset emails in this branch |
|---|---|---|---|---|
| English | Existing live language | Existing interface; regression checked | Existing templates retained | Explicit request language implemented |
| Arabic | Existing live language | Existing interface; regression checked | Existing RTL documents retained | Explicit request language implemented |
| French | Hidden | Existing private preview reconciled with current production source | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| German | Hidden | Account and trip dictionaries implemented; remaining website/booking interfaces outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Spanish | Hidden | Account and trip dictionaries implemented; remaining website/booking interfaces outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Turkish | Hidden | Account and trip dictionaries implemented; remaining website/booking interfaces outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Simplified Chinese (`zh-CN`) | Hidden | Account and trip dictionaries implemented; remaining website/booking interfaces outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |

The language registry's enabled flags and publication guard still permit only English and Arabic. Merely supporting a backend locale does not publish a website locale. Previous French checkpoint instructions to stop at French are superseded by the owner's new five-language scope, but historical verification limits still apply.

## Implemented in this checkpoint

- Reconciled `codex/language-foundation-20261001` (b9f6a0a) with production main a111eb476795. Resolved nine overlapping booking/payment component files, preserving Arabic presentation, French display translations, international country options, approved cancellation wording and locale on the final guest/signed-in payment request.
- Extended booking-owned language normalization to en/ar/fr/de/es/tr/zh-CN. Supported Simplified Chinese aliases normalize to zh-CN; Traditional Chinese identifiers are not silently represented as translated.
- Added five authored document catalogues. Booking confirmation, passenger cancellation, driver details, driver cancellation and reassignment use the language stored on the booking, independently of staff/webhook locale.
- Booking/cancellation PDF production functions use the new translated renderer. English and Arabic continue using their existing layouts. Existing stored PDF files are not regenerated.
- Welcome and password-reset emails use an explicit language from the registration/reset request. Fixed the existing password-reset sender that always selected its English body. No account-language database migration is introduced.
- Password-reset/request-code form labels, loading states, validation, failure states and successful reset feedback now have all seven languages. These two forms suppress generic backend-language toasts and show their own translated messages. Reset-code request feedback preserves account-existence privacy.
- Kept customer names, addresses, flight numbers, airline names, notes, third-party/provider names and identifiers verbatim. HTML output escapes untrusted content. Stored booking choices remain canonical; only their display text changes.
- New-language financial rows distinguish the stored commercial uplift from the separate airport fee and minimum-fare adjustment. No pricing, payment, refund, eligibility or webhook calculation changes.

## Verification at this checkpoint

- Ten offline backend tests pass. They execute the production email function bodies with delivery/Maps replaced, cover the five booking events across all five new languages, explicit welcome/reset language across all seven, opposite active staff language, language aliases, escaped customer content, unknown refund status and separate airport-fee presentation.
- EN/AR booking component, RTL, canonical-value and flight-time regression checks pass.
- Seven-language password-reset/request-code components render with the expected translated controls.
- Existing registry/hidden-route checks, French dictionary shape/placeholders and French payment-error mapping checks pass.
- TypeScript check passes for the reconciled frontend. A full Next.js production build with `--webpack` also passes. The default Turbopack attempt in the local restricted environment stalled during compilation and was cancelled; no claim is made that the default production-builder path was verified here.
- Fourteen synthetic PDFs generated using the production PDF function bodies: booking/cancellation in all seven languages. The ten new-language samples each fit one page after layout correction; their booking reference and localized title are extracted successfully. The ten new-language samples were visually inspected. Arabic controls remain one page; the unchanged English control layout produces two pages with this fixture.
- Chinese samples use an embedded Noto Sans CJK SC font in the isolated test environment. **This is not evidence that the font is installed on the VPS.**
- No production database, real booking, payment, email, OTP, account or support submission was used. No production merge, deployment or workflow activation was performed.

Reproduce from `act_backend-main` with Django 4.2, WeasyPrint, reportlab and pypdf:

```sh
PYTHONPATH=. python apps/trips/tests/test_customer_language.py
PYTHONPATH=. python apps/trips/tests/render_customer_languages.py --output /tmp/act-language-previews
```

The render command requires fontconfig and Noto Sans CJK SC (for example Debian's `fonts-noto-cjk`). It fails explicitly if that font is missing. Test samples use fictional contact details and never submit anything.

From `act_website-main`:

```sh
npx tsc --noEmit --incremental false
node scripts/check-booking-language.cjs
node tests/check-customer-account-languages.cjs
node tests/check-language-foundation.cjs
node tests/check-french-drafts.cjs
node tests/check-french-payment-errors.cjs
```

## Account and trip-management checkpoint (continued 3 October)

- Added complete customer account and trip dictionaries for German, Spanish, Turkish and Simplified Chinese: 142 account and 62 trip string values per locale, including protected status values. The server dictionary loader now resolves these draft sections. Publication gates remain unchanged.
- Filled the two existing Arabic fallback gaps (invalid phone and vehicle model) and localized the auth/trip route loading screen.
- Seven-language account feedback covers sign-in/registration failure, missing authentication, change-request/code failure, password update progress, account deletion and code resend. Country-name menus use the phone library's corresponding locale without altering E.164 values.
- Corrected email-change verification instructions in all seven languages: the existing backend sends the code to the current phone, not the new email address. No delivery channel or authentication policy changed.
- Corrected English/Arabic account-deletion notices to avoid promising that every record is removed, matching the existing French retention wording.
- Trip cancellation now sends `locale` (previously misspelled `loacle`), suppresses backend-language toasts, shows translated success/failure, disables repeated pending submissions and refreshes trip lists after success. Confirmation says cancellation rather than deletion; it does not promise a refund.
- Trip lists now key requests by locale and session, pass locale to recent-trip retrieval, and show a translated fetch failure instead of presenting a failed fetch as an empty history. Distance/duration units and pagination labels support seven languages.
- Account-change resend retains the entered code and cooldown state on failed requests, shows translated feedback and disables resend while pending or during the existing cooldown. No real OTP was requested.

Checks: seven-language production component SSR (login, registration, password/email/phone change, reset, trip cards and pagination), exact draft dictionary keys/placeholders and canonical trip statuses, escaped provider names, and production cancellation/email/phone confirmation handlers with external effects replaced all pass. Handlers cover both success and failure, canonical payloads, correct request locale, cache refresh only after success, and no cookie/profile success on failure. This is offline evidence, not browser/provider acceptance. TypeScript and the existing French dictionary checks pass. A full Webpack production build also passes. Subsequent dictionary/loading-only edits pass TypeScript and the targeted checks.

New action checks: `node tests/check-customer-account-actions.cjs` from `act_website-main`.

## Expanded coverage audit

The owner-requested audit on 3 October is recorded in [TRANSLATION_COVERAGE_AUDIT_2026-10-03.md](TRANSLATION_COVERAGE_AUDIT_2026-10-03.md). It adds explicit release gates for uploaded privacy/terms/FAQ/guide language selection, language switching without lost booking state, preference persistence, accessibility/transient states, provider-controlled text and all customer document entry points. The audit confirms these areas are not yet complete.

## Remaining work, in order

1. Complete German, Spanish, Turkish and Simplified Chinese dictionaries and customer interfaces. Generalise French-only routing, phone-country labels, date/time labels, payment-error handling and airport pages without changing stored API values. Finish remaining French hard-coded strings and outdated private notices.
2. Audit the full customer journey in every locale: home/airport entry, address suggestions, dates/times, passengers/bags, vehicle display, child seats, extras, flight details, guest and signed-in details, review, payment success/failure/retry, confirmation, account/profile, trip history, cancellation and support forms. Names/addresses returned by providers stay authentic; user-entered text is not machine-translated.
3. Translate the approved terms/privacy/customer instruction documents and all relevant customer-facing notifications; reconcile any remaining existing English/Arabic gaps. Separate staff/driver operational interfaces and provider-controlled receipt settings from customer-site translation. Do not claim that translating an ACT email changes Stripe's own receipts or bank authentication screens.
4. Verify real provider integration in a supported non-production/test-mode journey, including language persisted through payment initiation/webhook, booking/admin record, actual email output and PDF attachment/link. Offline model stubs and synthetic quotes do not establish payment, database or email-delivery acceptance. Do not use live customer charges or outgoing messages as a translation test without specific authorisation.
5. Confirm Chinese-capable fonts and run the document checks on the deployment environment. Review all desktop/mobile journey screenshots and final email/PDF previews. Keep GBP, approved policy and booking details consistent.
6. Prepare one concrete release with the locale guard, menus, dictionaries, SEO/hreflang/sitemap and backend support aligned. Publish only after the complete journey is verified and the concrete deployment is authorised. Record exactly which locales and release SHA are live.

Completion means a verified customer journey and matching communications for each language; translated files, a preview or an HTTP 200 alone do not meet that definition.

## Findings implementation — 3 October, documents and booking language switching

Implemented in the draft; not deployed:

- Instruction files now have an explicit language and a unique (document type, language) pair. Both public document endpoints select only the requested canonical language and active records; unsupported locales are rejected. Serializers expose the language and require it for creation or editing an unverified legacy record.
- Migration `admin_panel.0002_instruction_file_language` preserves existing file paths and records with blank/unverified language. It deliberately does not guess that old documents are English. Before production publication, inspect and label existing content and supply the actual translated files. Unverified files are excluded from the public API, so translated inline terms/privacy/FAQ remain the fallback. Do not reverse this migration after adding multiple language versions without a data-preserving rollback plan: the old unique document-type constraint cannot accommodate them.
- The admin upload/edit form offers all seven document languages independently of the admin UI language; duplicate checks are per language. Updating language/title/description/file increments the document version. Existing file type is included in full updates.
- Frontend selection also verifies document type and exact language. Terms/privacy no longer force French users to an English file. Modal fetches clear stale state and ignore obsolete responses, and PDF controls have seven-language labels. Missing localized app guides no longer silently link to an unlabelled static/environment fallback; the interface explains the absence and retains inline instructions.
- Before changing language, the booking UI hands off an allowlisted draft through same-tab session storage. It is consumed once in the destination locale, rejected after five minutes, and excludes vehicle quotes, prices, payment secrets and account credentials. Route/passenger/flight/seat/notes fields are restored without translating customer data; the journey returns to route review for a fresh quote. This is only a language-change handoff, not general draft autosave or session recovery.
- A language switch is blocked while a payment is being initiated or an existing payment is unfinished. A failed draft write also blocks navigation and shows a translated message, keeping the current booking open. Completed-payment state is not restored into another locale. Ordinary routes retain their query string and fragment. Selector accessibility/feedback has all seven languages; publication flags remain unchanged.

Validation:

- Four isolated SQLite/Django tests pass: old-schema migration and legacy retention, all seven exact public language selections, inactive/missing/invalid language handling, DB pair uniqueness, admin validation, content-version increment and migration/model consistency. These exercise real models/serializers and extracted production public view bodies, not the complete production application middleware stack or PostGIS database.
- `check-document-languages.cjs` passes exact locale/type filtering, wrong-language/unlabelled file rejection and translated viewer labels.
- `check-booking-language-draft.cjs` passes all seven draft destinations, one-time consumption, expiry, destination isolation, preserved canonical/customer values and secret/price exclusion.
- `check-language-switch-browser.cjs` passes against the local production build on desktop and mobile: EN→AR→EN route preservation, URL query/fragment retention, correct HTML language, consumed transfer and navigation blocked on storage failure. External services were blocked; quote responses were synthetic. Browser evidence is EN/AR only, since additional locales remain hidden. Payment-block behaviour and every later booking field still require full end-to-end browser acceptance.
- TypeScript, existing EN/AR booking regression, registry/hidden-route checks, French dictionary checks and the Webpack production build pass. The final admin wording adjustment is dictionary-only.

Commands (from frontend): `node tests/check-document-languages.cjs`; `node tests/check-booking-language-draft.cjs`; browser check needs Playwright and Chromium, optionally located by `ACT_PLAYWRIGHT_MODULE` and `PLAYWRIGHT_BROWSERS_PATH`.
Backend: `PYTHONPATH=. python apps/admin_panel/tests/test_document_languages.py` with Django 4.2 and DRF installed.

Remaining: translated document bodies/uploads and production migration preparation; remaining four website/booking/payment/support dictionaries; residual French/Arabic UI gaps; explicit preference persistence; full payment/provider/email/PDF/browser acceptance and coordinated publication. The coverage audit is a historical baseline; the fixes above address its document-selection and booking-transfer implementation findings but do not close the entire launch gate.
