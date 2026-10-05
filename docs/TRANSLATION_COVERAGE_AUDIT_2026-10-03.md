# Website translation coverage audit — 3 October 2026

**Latest implementation:** [Seven-language implementation and evidence — 3 October](SEVEN_LANGUAGE_IMPLEMENTATION_2026-10-03.md) supersedes the source-code gaps listed below. All seven customer catalogues and matching bundled documents are implemented and tested in the draft; production/provider acceptance and coordinated publication are still unverified. Earlier sections remain historical records.

Requested by the owner: check privacy, terms and conditions, FAQs, and anything affected by language changes or selection.

**Verdict: not complete; the five additional languages must remain unpublished.** This is a source and offline-test audit of draft PR #70, remote implementation commit `a3bc6db5d69718dc924728043d37d6f42aeb33a0` (local equivalent tree `8489f6d89b9e838110bf38d4f8cb1070af92bae3`). It is not a fresh production crawl, a review of uploaded production files, a legal-content review, or provider-delivery acceptance.

## Implementation update

The subsequent document-language and booking-transfer implementation is recorded in [MULTILINGUAL_CUSTOMER_JOURNEY_2026-10-02.md](MULTILINGUAL_CUSTOMER_JOURNEY_2026-10-02.md), under “Findings implementation”. The findings below describe the audited baseline, not the updated code. Document-language infrastructure and one-time booking transfer are now implemented/tested in the draft; actual translated uploads, additional locale UI and full acceptance remain pending.

## Confirmed release blockers at the audited baseline

1. **The uploaded-document system cannot select a document by language.** `act_backend-main/apps/admin_panel/models/instruction_files.py` has a globally unique `file_type` and no language field. Its public views filter only by active state and document type; `activate(locale)` does not translate the stored title, description or file. Public serializers do not expose a document language. The frontend `src/lib/api/fetchInstructionFile.ts` chooses the newest returned file without checking language. This affects terms, privacy, FAQ and passenger/driver guides. A translated button is not evidence of a translated document.
2. **Four languages still have only account and trip dictionaries.** `de`, `es`, `tr` and `zh-CN` lack `home`, `complaints`, `lostProperty`, airport and booking-interface catalogues. `src/lib/translation.ts` falls back to English for their missing sections. `src/lib/customer-text.ts` translates French only. Thus large areas of booking, navigation, content, policies and FAQs remain English if those locales were enabled now.
3. **Changing language can discard an unfinished booking.** `header/SelectLanguage.tsx` calls `window.location.assign`. It preserves the URL path, query and fragment, but `bookTaxi/index.tsx` holds route/form/passenger/flight/child-seat/car/step/payment state in React memory, with no booking-draft persistence found there. Reloading remounts that state. Browser acceptance must establish safe behaviour at each step, especially before/during payment. Do not persist sensitive payment data as a shortcut.
4. **Payment and navigation plumbing is not ready for all seven languages.** StripeWrapper's locale type is only en/ar/fr; payment-error mapping is French-specific; flight guidance and guest phone choices have French-specific branches. Locale types, operational-route redirects, SEO exclusions and menu accessibility labels also retain French-specific assumptions.

## Coverage matrix and required acceptance

| Surface | Evidence now | Still required before release |
|---|---|---|
| Privacy policy | EN/AR/FR inline catalogues each have 7 sections; FR explicitly requests the English uploaded file | Translate remaining four inline versions; select/version actual documents by language; verify displayed content, embedded file, download, title and description match |
| Terms and conditions | EN/AR/FR inline catalogues each have 18 sections; FR explicitly requests English PDF | Remaining four translations; localized actual files; keep approved cancellation/refund/waiting wording consistent in footer, checkout, emails and documents |
| Main FAQs | EN/AR/FR each have 10 inline Q&As; uploaded FAQ can override them | Remaining four translations; localized uploaded FAQ; English-only PDF controls in `Faqs.tsx` must be translated |
| Airport FAQs and landing pages | Existing EN/AR pages and separate French airport drafts | Complete DE/ES/TR/zh-CN airport pages, FAQs, metadata, calls to action and internal links; verify consistency with central policy |
| Document viewer | `Terms.tsx` and `Policy.tsx` have French/English control branches; `Faqs.tsx` has English controls | All seven open/download/close/loading/accessibility labels; reset cached file/fallback on locale change; reject or clearly identify a wrong-language file |
| Passenger/driver guides and app downloads | `DownloadAppTabs.tsx` fetches both instruction-file types from the same language-unaware service | Translated customer-facing download instructions, file metadata and actual guides; explicitly identify externally controlled app/store language; distinguish public driver guide from operational dashboard scope |
| Main content, About, footer, navigation | EN/AR/FR home dictionaries; `customerText` supports FR only | Remaining four catalogues; footer airport headings; copyright/accessibility text; locale-safe links rather than EN/AR-only prefix replacement |
| Booking steps | EN/AR regression checks and French draft work | All seven route, dates, times, passengers, bags, vehicle classes, seat requirements, extras, flight guidance, contact details, review, edit/back/continue, loading, validation and error paths |
| Vehicle labels | `localizedVehicleValue` selects English or Arabic database fields | Translate controlled categories/descriptions for other languages; retain authentic provider brand/model/registration and customer-entered values |
| Guest phone country menu | Extra countries remain gated by `locale === "fr"` | Localized country labels and equal international input capability for every locale; canonical phone values unchanged |
| Checkout and payment outcome | Explicit request locale exists; EN/AR/FR Stripe wrapper and FR error mapper | Provider-supported locale mapping including Simplified Chinese; validation/decline/3DS/timeout/retry/success messages; no duplicate payment on switching/reloading/back navigation |
| Account and profile | New DE/ES/TR/zh-CN account catalogues; seven-language form renders and selected handlers checked | Browser verification of actual auth/profile/loading/modal states and backend failures; any remaining verification component paths; ensure no hidden English flashes/fallbacks |
| Trip history and cancellation | Seven-language trip catalogues, cancellation feedback, units and pagination; locale typo fixed | Browser acceptance of fetch failures, expired sessions, cancellation outcomes and updated history; preserve booking-owned email language regardless of page/staff locale |
| Complaints and lost property | EN/AR/FR dictionaries; French-only error/date/native-validation branches | Remaining four dictionaries and all validation, upload, status, empty/error/loading, contact preferences, response and notification paths |
| Email and booking/cancellation PDFs | Five booking-event email kinds, welcome/reset and two PDF kinds implemented across seven; offline evidence exists | Inventory any other customer notification paths; verify actual delivery/attachments/links and production Chinese fonts; match booking-owned locale with no ambient worker-language leakage |
| Third-party receipts, bank screens, map suggestions | ACT code does not control all external text | Document/configure provider language options where supported; verify test-mode handoff/return; do not claim ACT translations automatically translate Stripe receipts, bank challenges, app stores or proper place names |
| Language selector | Native labels and enabled-locale list; only EN/AR enabled; URL query/fragment retained | Seven-language accessible selector label, keyboard/mobile behaviour, same-page routing and safe draft preservation; test every source/target pair |
| Language preference and entry routes | Browser Accept-Language negotiation and URL locale; default Arabic; production-domain root has an English redirect | Define explicit-choice persistence and precedence versus browser/default language; verify locale aliases, deep links, refresh, root entry, bookmarks and back/forward; no preference persistence found in selector |
| Role routes | French-only redirect to English for driver/admin/upload routes | Generalize safe operational-language fallback for all additional customer languages without changing authorization or stranding users |
| SEO and page language | Registry-driven sitemap/hreflang, root html lang/dir; French-specific noindex/publication exclusions | Enable only fully accepted languages; correct all page titles/descriptions, canonical/hreflang/sitemap, html lang/dir, noindex removal and structured FAQ content where present |
| Accessibility and transient text | Some translated labels; auth/trip loaders corrected | Audit aria labels, alt text, tooltips, required/invalid messages, modal buttons, OTP digit labels and mobile controls; customer-wide loading/error/not-found screens still need coverage |
| General loading and 404 | 404 uses `home` dictionary; site segment loader still says `Loading page...` | Translate all customer route loaders and error states, not just auth/trips; verify wrong/unsupported-locale handling |
| Cookies/tracking/preferences | Google Ads script present in root layout; no dedicated consent/preferences component found in scanned source | Include any deployed or provider-injected consent/privacy/preferences interface in language acceptance. This audit makes no legal-compliance determination and has not inspected runtime-injected UI |
| Formatting and preserved data | Some locale-aware date formatting; support forms use AR/FR/EN branches; booking currencies remain GBP | Seven-language dates/times/numbers/plurals/timezone cues, RTL layouts and CJK fonts; GBP remains GBP; do not translate personal names, addresses, flight IDs, provider values or stored API enums |
| Image/video/embedded text | Asset and document entry points inventoried, not every image visually reviewed | Review all customer-visible images, screenshots, banners, embedded maps and downloads for baked-in text; localize or explicitly mark externally controlled content |

Paths beginning `src/` above are under `act_website-main/`.

## Checks rerun for this audit

- `node tests/check-language-foundation.cjs`: passes registry/hidden-route/path/fallback checks; EN/AR audited dictionary sections now have no missing fallback keys.
- `node tests/check-french-drafts.cjs`: passes source shape, tokens, route targets, protected values and hidden-state checks.
- `node tests/check-customer-account-languages.cjs`: passes seven-language account/trip component rendering and dictionary contracts.

These checks confirm their defined scope. They do **not** establish full-site translation completeness, actual uploaded-file language, browser state preservation, linguistic quality, provider acceptance or current live publication.

## Completion gate

For each of en/ar/fr/de/es/tr/zh-CN, review desktop and mobile evidence covering: public entry → language selection → full booking → guest/signed-in checkout → payment success/failure/return → matching email/PDF → account/trip management/cancellation/support. Exercise switching languages mid-flow and reopening every legal/FAQ document from both footer and checkout. Verify inline and downloadable document versions independently. Include all transient, accessibility, error and external-provider states listed above.

First resolve the document-language model/selection and booking-state switching behaviour, then finish missing catalogues and component branches, then perform full browser/provider/document acceptance. The language registry must not be used as a substitute for those checks.
