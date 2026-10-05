# Seven-language implementation — 3 October 2026

Status: ACT-authored customer translation implementation and bounded offline/browser checks complete in draft PR #70. **Not deployed; not production/provider acceptance.** English and Arabic publication flags remain enabled; French, German, Spanish, Turkish and Simplified Chinese remain disabled in the repository until the coordinated release gate is satisfied.

## Customer coverage

| Area | Implemented coverage |
| --- | --- |
| Public site | Home, navigation/footer, About/contact, downloads, five airport landing pages, page metadata, customer loaders and 404 |
| Booking | Route/airport selection, quote and vehicle categories, passengers and international country labels, child/infant seats, flight guidance, notes, review, ACT payment errors and confirmation |
| Account and trips | Sign-in/signup, password reset, profile/account changes, verification controls, deletion, trip history, cancellation and feedback |
| Support | Complaints and lost property: form, validation, upload labels, list/status/detail, empty/loading/failure and retry states |
| Legal/help | Seven privacy sections, eighteen terms sections, ten FAQs in every language; unchanged approved policy and GBP amounts |
| Downloads | 35 versioned PDFs: privacy, terms, FAQ, passenger app installation and driver app installation in each language |
| Communications | Welcome/password-reset plus five booking-event email types and booking/cancellation PDFs; links use the corresponding booking-owned document |
| Owner/operations | New booking, driver acceptance, passenger cancellation, driver cancellation and onboarding admin messages run under explicit English; customer-entered names, addresses and notes stay verbatim |

The app instruction PDFs reproduce the website installation instructions. They are not translations of any unseen operational manuals or unverified legacy uploads. Exact-language uploaded documents take precedence over bundled documents; their content must be inspected before assigning a language in production.

## Repairs made during final verification

- Added complete DE/ES/TR/zh-CN public, legal, support, booking and airport catalogues and seven-language runtime controls.
- Replaced the English-only signup image with translated HTML text; localized active image/accessibility labels, date/time controls, map/quote/download/support failure states and units.
- Bundled licensed CJK font subsets for the website and generated PDFs. Coverage checks include Chinese country-menu labels. System font fallback remains applicable to arbitrary customer input outside the catalogue subset.
- Corrected restored date/time display and controlled passenger/luggage fields, so language switching carries current input. Resets quotes/payment state rather than reusing stale amounts. Mobile location errors no longer cover the language selector.
- Explicit locale preference cookie survives root entry. Query/fragment and same-page destination are preserved. Operational routes for additional languages resolve to English without changing authorization.
- Stripe Elements maps all supported languages (Simplified Chinese uses `zh`); ACT validation/decline/unknown-payment messages are translated and unknown payment outcome directs the customer to check before retrying.
- The English cancellation email was missing its PDF link despite having the URL in context. Added and tested the actual booking/cancellation email links under different staff languages.
- Owner notification functions force English independently of the booking/customer locale. No translation or replacement of customer-written notes.
- Account-change SMS passes the explicit request locale to Twilio Verify; no phone-country guess overrides the website choice. Other callers without a locale retain provider defaults. Real delivery/template configuration remains unverified. Reference: https://www.twilio.com/docs/verify/supported-languages (checked 3 October 2026).
- Aligned old EN/AR confirmation copy with the documented approximately-two-hours-before-journey wording. Corrected display labels for the commercial uplift, without changing price calculations. Existing English/Arabic combined uplift/airport PDF row is labelled as combined charges.
- Preserved the VPS scheduler virtualenv group-access repair in the repository deployment script so a later deployment does not erase that fix.

## Evidence

- TypeScript and production Webpack build pass.
- Complete seven-language catalogue checks pass: source keys, nonempty strings, placeholders, canonical values, policy/FAQ counts, booking/date/time renders, payment feedback and 25 additional-language airport page renders.
- Account/trip rendering, account action success/failure, hidden-locale foundation, French contract, exact-language document selection and draft storage/expiry checks pass.
- Browser checks in an isolated all-language build: two viewports (1440×1000, 390×900), all 42 distinct source/destination pairs per viewport, route/date/time/luggage preservation, cookie preference and 42 matching legal PDF openings pass. Repository publication flags were never enabled.
- Fourteen synthetic booking journeys pass: route → mocked quote → passenger → child-seat validation → flight skip → notes → review. No booking/payment creation button was pressed.
- Existing EN↔AR browser regression passes, including storage-failure navigation blocking.
- Thirteen backend language tests pass with external side effects substituted: explicit customer language, ambient-language isolation, actual email PDF URLs, four owner booking-event paths, safe content and SMS locale arguments.
- Twelve actual production booking/cancellation PDF function renders pass across AR/FR/DE/ES/TR/zh-CN. Chinese font is embedded. Final PDF pages visually inspected for Arabic direction, Chinese glyphs, clipping and page breaks.
- All 35 static PDF hashes match their exact dictionary source and file bytes; no empty/orphan pages; Chinese catalogue glyph coverage passes. Seven terms PDFs are two pages; other downloads one page each.

Browser quote/API data were synthetic. All external browser calls were blocked. These results do not prove Google/Stripe/Twilio/email delivery, authenticated production submissions or a live release.

## Deployment and actual-service gate

1. Apply document-language migration `admin_panel.0002_instruction_file_language` in the approved backend release; inspect/classify legacy uploaded documents. Never guess their language. Bundled documents supply missing language/type combinations.
2. Deploy candidate backend/frontend to a supported test environment; verify Google Places, Stripe test-mode success/decline/3DS/return, account OTP delivery and customer/internal email delivery with matching PDF URLs and persisted booking language. Confirm production service-account font/file access using the offline PDF check there.
3. Verify authenticated account, trip cancellation and support requests against the real test backend. Inspect actual provider-injected/hosted text (Stripe receipts, bank challenges and SMS templates) and any production-only content/uploads; those are not automatically translated by ACT catalogues.
4. Deliberately enable all five completed additional locales, remove the preview-only exclusions from publication helpers, then verify canonical/hreflang/sitemap and the exact deployed release. Current `publishedLocalesFor` retains a historical French exclusion that must be removed at activation together with the registry guard, not silently during this draft.

No production deployment, payment, real booking, email or OTP was initiated in this verification. Existing stored booking PDFs were not rewritten. AI agents/Gemini/n8n handover remains a separate workstream after the language release.

## Reproduce

Frontend: `node tests/check-complete-customer-catalogues.cjs`, `node tests/check-document-languages.cjs`, `node tests/check-customer-account-languages.cjs`, `node tests/check-customer-account-actions.cjs`, `node tests/check-booking-language-draft.cjs`, `node tests/check-language-foundation.cjs`, `node tests/check-french-drafts.cjs`, `npx tsc --noEmit` and `npm run build -- --webpack`.

PDF assets: `python scripts/check-customer-documents.py` needs pypdf/fonttools. Rebuild with `ACT_CJK_FONT=/path/to/NotoSansCJKsc-Regular.otf python scripts/build-customer-documents.py`; rebuild the licensed font subsets with the same variable and `scripts/build-customer-font.py` (fonttools[woff]).

Browser: `node tests/prepare-seven-language-preview.cjs` prints a disposable copy path. Build that copy with a synthetic Google key and API URL `http://127.0.0.1:3001`; run `tests/check-seven-language-browser.cjs` and `tests/check-seven-language-journeys.cjs` from the real frontend with `ACT_PREVIEW_DIR` set to the copy. `ACT_PLAYWRIGHT_MODULE` and `PLAYWRIGHT_BROWSERS_PATH` may identify an installed Playwright/Chromium. `ACT_SCREENSHOTS` is an optional local evidence directory. Never use production credentials for these tests.

Backend: `PYTHONPATH=. python apps/trips/tests/test_customer_language.py`; `PYTHONPATH=. python apps/trips/tests/check_customer_pdf_rendering.py` (Django, WeasyPrint and pypdf). No database or outbound provider calls.
