# Passenger, flight and review handoff audit — 2026-10-04

**Status: draft fixes committed to PR #71. Not merged or deployed. Historical successful owner-reported test trips remain preserved as prior evidence; this slice requires regression testing after the changes.**

## Reproduced findings and fixes

### Multi-stop payment consistency
The initial quote request includes ordered `stop_points`, and the backend quote route calculation uses them. In `ConfirmFlightDetails`, the final initiate-payment request constructed the same stop list but left the assignment commented out. Both signed-in and guest payment endpoints recalculate authoritative distance/price from the request and read `stop_points`; therefore a multi-stop quote could be handed to payment as a direct pickup-to-drop-off route.

Fix: include the same ordered stop coordinates in the initiate-payment body whenever stops exist. No fare formula/rate changed.

### Passenger contact validation
The passenger screen previously checked only non-empty values. The guest backend validates email and field lengths, but the signed-in path can persist the supplied contact fields without equivalent request-level validation.

Fix: before review/payment, validate email shape and construct an international phone number from the selected calling code + entered number using `react-phone-number-input` validation. Add accessible error output, trim name/email, and align UI max lengths with guest backend limits (name 255, email 254, phone 32). Add autofill hints. Backend remains authoritative.

### Stale child/infant choices
If a passenger went back and changed child/infant counts to zero, previous seat choices could remain in state and still be sent in `booking_details` even though the review hid them.

Fix: when the first-step counts are committed, clear the corresponding stored seat choice if that passenger category is now zero.

### Stale opposite flight time
For manually classified journeys, switching between arrival and departure could retain the previously entered opposite time in state and send both values.

Fix: selecting Arrival clears departure time; selecting Departure clears landing time. Existing airport-direction auto-selection behaviour is preserved.

### Review accuracy
- The review labelled the booking pickup time as `ETA`. It now says **Pickup Time**.
- The review contained a large hardcoded fallback encoded route. If the real quote polyline was absent, the page could display an unrelated route. The fallback was removed; the existing localized map-unavailable state is shown instead.
- The review always displayed **Meet & Greet — Included**, while the payment payload currently sends `meet_and_greet: false`. The unsupported claim was removed. This does not decide ACT's future meet-and-greet product policy.

## Open decisions/findings

- The Flight Details page currently allows **Skip — Not applicable for this journey** even when pickup or drop-off is a detected airport. The audit has not changed this because requiring flight details is an operational/business rule that should be confirmed rather than guessed.
- Flight number and airline are currently optional; landing/departure time becomes required only when a flight type is active. No new mandatory flight-number policy was introduced.
- Additional driver notes remain optional. No arbitrary new character limit was introduced in this slice.
- Review/payment still requires full browser/backend/provider regression.
- Pricing display terminology (including whether the 20% component is correctly described as VAT versus an uplift) should be reviewed with the pricing-policy slice; no tax/pricing semantics were changed here.

## Required regression scenarios

1. Guest and signed-in passenger with valid/invalid email and UK/international phone formats.
2. Adult-only booking; child booking; infant booking; go back and remove child/infant then confirm no stale seat data is sent.
3. Airport pickup auto-arrival; airport drop-off auto-departure; city-to-city manual/no-flight flow; airport-to-airport/manual case.
4. Switch arrival -> departure and departure -> arrival and inspect payload.
5. One stop and multiple stops: initial quote route/distance/price versus payment-authoritative route/distance/price must agree for unchanged inputs.
6. Back/edit from review and repeat payment initiation without stale vehicle/payment state.
7. Route polyline present and absent; absent state must never display an unrelated route.
8. Confirm review values exactly match payload values before Stripe test-mode execution.
