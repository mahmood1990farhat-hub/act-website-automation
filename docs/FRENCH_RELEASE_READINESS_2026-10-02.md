# French release readiness — 2 October 2026

Status: focused implementation complete on the unpublished language branch;
verification pending. This is NOT a production release or live-payment acceptance.

## Completed changes

- French passenger country selector uses the existing phone library's international
  country/calling-code metadata, including France +33, Belgium, Switzerland and
  Canada. Existing eight stored values and English/Arabic selectors are preserved;
  added values keep English country names for the existing backend snapshot format.
- Signup and change-phone country labels are French. Passenger details remain
  explicit user input; no phone number is silently rewritten.
- French Stripe Elements locale and French ACT error messages for common card
  errors; unknown errors ask customers to verify payment state before retrying.
  English/Arabic retain their existing provider-auto behavior. Amounts, currency,
  payment status and conversion logic are unchanged.
- French login/signup error handling, left-to-right auth layout, and driver-tab
  navigation to the English driver interface. No authentication bypass.
- French complaint/lost-property validation uses existing translated messages;
  dates and submission-error fallback are localized. No support records sent.
- French About/contact page uses ACT email/telephone links in place of the existing
  non-submitting contact form. The page explicitly says email opens the customer's
  email app; it does not claim to send a message.
- Terms/privacy PDF controls are translated, request existing English documents,
  and visibly identify their language. External-provider messages may still be English.
- French airport WebPage/Service/FAQ structured data derived from visible content;
  French download/support page metadata. French remains noindex/nofollow and absent
  from sitemap/alternate publication. No guarantee of search rich results.
- French deletion warning now follows existing privacy retention wording instead
  of promising destruction of all records.

## Source-grounded wording decisions

Read the current ACT_Master_Operations_Document.docx version 1.1, issued
8 September 2026 (Library version 1). Its confirmed commercial rule is a 20%
uplift, not a new VAT decision. French price labels now say “Majoration commerciale
(20 %)”; backend `regular_vat` field names/calculations are untouched.
The standard customer journey specifies driver details approximately two hours
before the journey. French confirmation now describes that intended timing,
replacing the source website's one-hour-after-booking promise. This copy correction
is not proof that the scheduled driver-message automation is operational.

## Remaining release gates — do not silently approve

1. **Cancellation/refund policy:** the master explicitly marks the full schedule
   unapproved. Current website terms promise full refund more than 24 hours ahead
   and no refund for late cancellation/no-show; FAQ wording differs. The hidden
   French draft retains these source terms pending a business decision. Do not
   publish it as approved policy. Prepare one consistent approved cancellation,
   amendment, no-show/waiting and refund policy across English/Arabic/French and
   provider PDFs; this task does not rewrite the live contract.
2. **Other unconfirmed source promises:** six-week lost-property retention,
   five-working-day complaint response, availability/app/notification claims and
   child-seat/flight advice still need operational confirmation or a focused copy
   correction. The flight-time suggestion uses a fixed 2–3-hour pickup window
   without route duration; it must not be represented as route-aware airport-arrival
   advice. These are existing source gaps, not completed multilingual features.
3. **Provider/transaction acceptance:** the private build blocks external traffic.
   Real Google Places, Stripe iframe/errors, guest/payment initiation, booking record,
   admin visibility, email/PDF and authenticated account/support submissions have
   not been newly accepted. Use a supported test environment/provider test mode;
   never charge a real customer to approve a translation. The master itself warns
   that payment/admin/email must be verified after infrastructure changes.
4. **Publication:** remove private-preview wording, enable French deliberately,
   update sitemap/hreflang/indexing together and obtain owner release approval.
   Main auto-deploys. Keep all other new languages hidden.

## Bounded verification

Build/type check, source hidden-state/dictionary checks, display-only payment-error
checks, existing English/Arabic routes/booking-entry, French metadata/schema,
desktop/mobile contact/auth/support validation and synthetic quote-to-review.
No valid account/support request, booking, payment, email or OTP is sent.
Stop after a successful candidate pass; repair concrete failures only.

Final evidence will be recorded after the check finishes.

Next recommended task: settle the cancellation/refund policy conflict, then
complete the specific provider/transaction acceptance gate before requesting
French production release approval. No new language or automation expansion.
