# Booking validation findings — 2026-10-04

Status: draft implementation on PR #71; not merged or deployed.

## Confirmed source findings
- Owner clarification: the earlier 24-hour online-booking rule was later changed to 3 hours. The backend's existing 3-hour enforcement was therefore the current intended rule; the stale 24-hour comment caused the audit misinterpretation.
- The over-eight-suitcase validation returned an unrelated 3-hour booking message.
- Frontend number inputs had min/max hints, but quote construction did not independently enforce integer/nonnegative counts or total online limits.
- Vehicle filtering already requires max_passengers_count >= requested passengers; serializer also rejects passenger count above 7.

## Changes in this slice
- Correction after owner clarification: restored the backend threshold to 3h and updated the stale comment to state the current 3-hour online-booking rule.
- Backend lead-time comparison explicitly constructs the pickup datetime in Django's current timezone.
- Corrected the over-eight-suitcase message to describe the luggage limit.
- Quote payload boundary now requires 1–7 passengers, nonnegative integer luggage and <=8 total suitcases.
- First booking screen checks adults/children/infants/luggage as whole nonnegative values before a quote request.
- Existing downstream quote/vehicle/payment state is invalidated only after route/date/time/count validation succeeds and immediately before the fresh quote request.
- Extended isolated quote-helper regression cases for count boundaries.

## Important limits
- No production request, booking, payment or deployment was made.
- Browser/UI, Django suite and full application build still need execution in a suitable checkout/test environment.
- The 3-hour rule must be exercised at the exact boundary, just below/above boundary, midnight and UK DST transitions.
- Server-side validation remains authoritative; frontend validation is user feedback/defence in depth.
- The UI currently permits selecting today's date; this is acceptable only if submit/server validation prevents a <3h quote. A future UX improvement can disable impossible date/time combinations without becoming the authority.
