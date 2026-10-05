# French private preview — 2 October 2026

Scope: actual ACT Next.js customer interface in an isolated test build. This is
not a deployed French site and is not release approval.

## Implemented

- Explicit French dictionary loaders with English fallback for omitted operational
  sections. Application registry still disables French; English/Arabic only.
- Shared French template for all five airport pages, with their draft metadata.
- French homepage, navigation, footer links and main booking interface text.
- French date labels/months and time-picker labels, preserving existing serialized
  date/time formats and AM/PM selection. No pricing/payment arithmetic changes.
- Passenger fields, flight labels/advice, child-seat display labels, journey
  review and confirmation labels; stored child-seat values remain English.
- Safe English airport/vehicle names when French database fields do not exist.
- Locale-based confirmation links instead of inferring a language from a numeric
  notification-time translation.
- Driver/admin destinations fall back to English through existing authentication
  checks; a visible French explanation is provided. No auth bypass introduced.
- French preview notice explains English addresses, vehicle descriptions,
  email/PDF and GBP payments; it does not promise French telephone support.

## Isolation

The test-only `prepare-french-preview.cjs` enables French in the disposable Docker
image after checking that the stored application configuration keeps it disabled.
No application environment switch enables French on production. The container
binds its server to loopback, has no network and no published host ports. Browser
requests use synthetic places/quotes; all real external calls are blocked.
French public-page metadata is noindex/nofollow and sitemap/alternate publication
continues to exclude French, even in this test image.

## Evidence

Build/TypeScript, hidden-registry checks, the five dictionary checks and all 12 English/Arabic public routes passed. Existing English/Arabic booking-entry checks passed. Final French browser checks passed on desktop and mobile in run 36977941355 (job 110745766995), candidate `beb309ecd318f5fb4b92094ea8375ff261ce6907`. Artifact 11214192069 contains 14 screenshots and result.json. Two synthetic quotes, zero real bookings, zero payments. Six expected offline Stripe loader errors were reported; no unexpected browser errors. Check run: https://github.com/mahmood1990farhat-hub/act-website-automation/actions/runs/36977941355 .
The browser check covers all five French airport pages and desktop/mobile
navigation, date/time entry, simulated quote, vehicle choice, passenger validation,
flight step, notes and review. It stops before booking/payment creation.

English/French screenshot pairs come from the same candidate build; the English
images are reference views, not new production captures. Viewport screenshots
show the top of each screen; full Heathrow images are supplied separately.
No screenshot represents a real reservation or payment.

## Remaining before a French release

- Review the existing source claims recorded in FRENCH_TRANSLATION_REVIEW_2026-10-02.md:
  driver-notification timing, tax label, cancellation/retention/privacy wording,
  service availability and child-seat/flight guidance. They were not silently
  redefined as part of translation.
- Finish remaining edge text/provider errors and check localized auth/support
  interactions; those dictionaries being loaded is not functional acceptance.
- Add/check the appropriate international phone choices: the existing passenger
  form still has eight countries and no France +33 option.
- Confirm Stripe's locale/error behavior and any remaining external-provider
  controls in a separately scoped check. Real Maps/Places, backend booking,
  payment and post-booking email/PDF are not accepted by this isolated preview.
- Review airport structured-data publication and final metadata for all customer
  routes. The French template is a draft preview, not an indexed SEO release.
- Remove preview-only copy only as part of a concrete approved release; enable
  French deliberately, then deploy and verify. Main auto-deploys production.

Next task: resolve the small French release checklist and present the exact
release for approval. Do not translate another language or expand automation
infrastructure before completing this first language.

Earlier runs found and fixed driver year-picker and airport-name type boundaries. A standalone TypeScript invocation needed Next image declarations, so the normal Next build remains authoritative. Two browser selectors were corrected to match the labelled time control and visible mobile CTA; acceptance assertions were retained. Verification stopped after the final successful run.
