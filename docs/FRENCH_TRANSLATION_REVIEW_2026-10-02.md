# French customer-facing translations — draft for review

Status: translation preparation complete for the scope below; NOT reviewed,
NOT integrated, NOT deployed, NOT a complete French booking acceptance.

Source: website commit `99da9c773f5eb3322c13940603dc383e71fb0653`.
Branch: `codex/language-foundation-20261001`.
All added content is inert JSON. The application loader, locale registry,
middleware, sitemap, metadata generation and production branch are unchanged.
French stays disabled; copying these files does not enable a language.

## Completed

- [x] `home.json`: navigation, footer, homepage/booking dictionary, about/contact,
  terms/privacy, general FAQs, public app-download descriptions and error page.
- [x] `auth.json`: login, passenger signup, account verification, password reset,
  password/email/phone changes and profile. Exactly four driver/admin sections
  are intentionally omitted: CreateCaptainAccount, driverOnboarding,
  GetStartedCaptain, admin_login. Do not count English fallback as translation.
- [x] `tripsPassenger.json`, `complaints.json`, `lostProperty.json`.
- [x] `airports.json`: Heathrow, Gatwick, Stansted, Luton and London City copy,
  metadata and service description, retaining existing route slugs. Common copy
  is shared, not five duplicate page components. Replace `{airport}` using the
  selected page's airport value; use London City's paragraph and vehicle-FAQ
  overrides (vehicleFaq replaces shared FAQ index 2). These are draft data,
  not rendered pages or published SEO.
- [x] `bookingSupplement.json`: draft labels for the inspected passenger,
  flight, child-seat and checkout/confirmation components, plus explicit English
  fallback notices. These labels still need wiring; they do not translate the
  current hard-coded UI automatically.
- [x] One offline structure/invariant check: PASS. The five existing dictionary
  shapes contain 705 string values including URLs, machine values and proper
  names (296 home, 142 passenger/shared auth, 89 complaints, 116 lost property,
  62 passenger trips). This is NOT a claim of 705 newly translated phrases.
- [x] All five airport entries present; array lengths, interpolation tokens,
  route targets/anchors, phone numbers, email, postal address, GBP, status values
  and download filenames checked. French disabled/source loader exclusion checked.

Run from the frontend directory: `node tests/check-french-drafts.cjs`.
No build rerun is needed for unimported data; content-only checkpoint uses
`[skip ci]`. No screenshot, provider request, payment, booking or customer message
was generated. The prior foundation acceptance remains a separate checkpoint.

## Short review sample

| Use | French draft |
| --- | --- |
| Main headline | Vos transferts aéroport et en ville, en toute simplicité |
| Price button | Obtenir un tarif |
| Pickup field | Lieu de prise en charge |
| Airport heading | Transfert aéroport Heathrow – Londres |
| Book button | Réserver maintenant |
| Contact | Nous contacter |
| Passenger details | Coordonnées du passager |
| Payment | Informations de paiement |
| Lost property | Objets perdus |
| Complaints | Réclamations |

Tone: neutral French using **vous**. ACT, Airport & City Transfer, TfL and DBS
remain named entities. Airports, addresses, backend values and GBP are not
translated or converted. Date/Distance/Description and other identical French
words are valid translations, not missing content. File and URL keys retain
existing spelling, including legacy typos used by components.

## Review items before publication — no policy changes made

These drafts translate existing source claims, not independently verified policy.
Legal wording is a translation draft, not legal validation or a revised contract.

1. **Driver-detail timing:** source confirmation promises within 1 hour; an
   unused 5-hour string is also present. Confirm the intended operational timing
   before publication. The existing BookingConfirmation component chooses an
   English/Arabic trips URL from that numeric text; replace that with a locale
   link during integration. Do not manipulate the number to control routing.
2. **Prices/tax:** the existing dictionary labels 20% as VAT. Confirm that label
   matches actual fare/tax treatment before releasing French. No rates, fees,
   currencies or calculations changed here.
3. **Policies:** source terms promise full refunds above 24 hours, no refund for
   late cancellations/no-shows, 6-week lost-property storage and a 5-working-day
   complaints response. Its FAQ uses softer cancellation wording. Review these
   together, plus liability, licensing, accessibility and availability claims.
4. **Privacy/account deletion:** source profile text promises all data is deleted
   permanently, whereas privacy terms permit required retention. Resolve this
   source inconsistency rather than independently rewriting French policy.
5. **Service/app claims:** immediate confirmations, notifications, 24/7 support,
   app downloads, guaranteed bookings and instant driver earning are source
   claims, not verified capabilities. Driver onboarding still requires approval.
   Public app descriptions are translated; the apps/PDFs themselves are not.
6. **Child-seat and flight advice:** supplementary strings faithfully draft the
   existing text, including its age/height ranges and 2–3-hour departure advice.
   Review for correctness and actual route travel time before publication; do
   not treat translation as safety/legal approval. Backend child-seat option
   values currently use English sentences: translate labels only, retain values.
7. **Telephone country selection:** current form has eight hard-coded countries
   and no +33 France. Draft labels preserve those values. Confirm proper
   international-number support during integration; translating the labels alone
   does not fix this limitation.

Two deliberate editorial proposals are recorded for review: the obsolete ATG /
Airport taxi Transfer Company branding in public copy is rendered as Airport &
City Transfer, and “no language barriers” is omitted to avoid suggesting French
telephone support. No new discounts, fares or service guarantees were added.

## Incomplete / next bounded task

- [ ] Review French meaning and the source-policy items above; no owner approval
  of these new French drafts has been recorded.
- [ ] Connect French dictionaries and shared airport data in an isolated preview
  while leaving public French disabled. Keep driver/admin on explicit en/ar
  destinations with the supplied explanation and preserve authentication.
- [ ] Finish the remaining hard-coded customer strings, component locale types,
  safe locale links, date/time widget labels, ACT checkout errors and provider
  locale mapping. Inventory route/location/vehicle/contact controls during that
  integration; this supplement is not an exhaustive extraction of the app.
- [ ] Apply the fallback notices: address suggestions, some vehicle descriptions,
  email/PDF and driver/admin remain English where applicable. No new translation
  service, database language columns or backend release is required for drafts.
- [ ] Produce actual desktop/mobile screenshots and perform one scoped French
  navigation/booking-entry check. Do not use a mock-up as live evidence.
- [ ] Obtain explicit release approval before enabling French, merging to main
  or deploying. Main auto-deploys production.

Next recommended task: integrate these drafts into a private French preview,
complete the remaining customer-interface strings, and show desktop/mobile
screenshots with French still hidden from the live website.
