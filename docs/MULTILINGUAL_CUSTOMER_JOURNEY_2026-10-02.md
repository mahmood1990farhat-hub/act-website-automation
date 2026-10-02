# ACT customer-language completion workstream

Started 2 October 2026 after the owner's instruction to prioritise **all five additional languages, including emails and the complete booking journey**. This workstream comes before resuming Gemini/n8n operational handover. Those tasks remain pending; they have not been cancelled.

**Status: first implementation checkpoint; incomplete and unpublished. Not a release candidate or a completed five-language launch.**

## Scope and current position

| Language | Public website | Customer frontend | Booking emails and PDFs in this branch | Welcome/reset emails in this branch |
|---|---|---|---|---|
| English | Existing live language | Existing interface; regression checked | Existing templates retained | Explicit request language implemented |
| Arabic | Existing live language | Existing interface; regression checked | Existing RTL documents retained | Explicit request language implemented |
| French | Hidden | Existing private preview reconciled with current production source | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| German | Hidden | Full customer dictionary and interface work outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Spanish | Hidden | Full customer dictionary and interface work outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Turkish | Hidden | Full customer dictionary and interface work outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |
| Simplified Chinese (`zh-CN`) | Hidden | Full customer dictionary and interface work outstanding | Five event types and two PDF types implemented/offline tested | Implemented/offline tested |

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

## Remaining work, in order

1. Complete German, Spanish, Turkish and Simplified Chinese dictionaries and customer interfaces. Generalise French-only routing, phone-country labels, date/time labels, payment-error handling and airport pages without changing stored API values. Finish remaining French hard-coded strings and outdated private notices.
2. Audit the full customer journey in every locale: home/airport entry, address suggestions, dates/times, passengers/bags, vehicle display, child seats, extras, flight details, guest and signed-in details, review, payment success/failure/retry, confirmation, account/profile, trip history, cancellation and support forms. Names/addresses returned by providers stay authentic; user-entered text is not machine-translated.
3. Translate the approved terms/privacy/customer instruction documents and all relevant customer-facing notifications; reconcile any remaining existing English/Arabic gaps. Separate staff/driver operational interfaces and provider-controlled receipt settings from customer-site translation. Do not claim that translating an ACT email changes Stripe's own receipts or bank authentication screens.
4. Verify real provider integration in a supported non-production/test-mode journey, including language persisted through payment initiation/webhook, booking/admin record, actual email output and PDF attachment/link. Offline model stubs and synthetic quotes do not establish payment, database or email-delivery acceptance. Do not use live customer charges or outgoing messages as a translation test without specific authorisation.
5. Confirm Chinese-capable fonts and run the document checks on the deployment environment. Review all desktop/mobile journey screenshots and final email/PDF previews. Keep GBP, approved policy and booking details consistent.
6. Prepare one concrete release with the locale guard, menus, dictionaries, SEO/hreflang/sitemap and backend support aligned. Publish only after the complete journey is verified and the concrete deployment is authorised. Record exactly which locales and release SHA are live.

Completion means a verified customer journey and matching communications for each language; translated files, a preview or an HTTP 200 alone do not meet that definition.
