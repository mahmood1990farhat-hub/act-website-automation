# Booking validation findings — 2026-10-04

Status: draft implementation on PR #71; not merged or deployed.

## Confirmed source findings
- The backend TripSerializer contained a comment saying 24-hour advance booking but enforced only 3 hours. ACT's approved website rule is online bookings at least 24 hours ahead; within 24 hours contact ACT.
- The over-eight-suitcase validation returned an unrelated 3-hour booking message.
- Frontend number inputs had min/max hints, but quote construction did not independently enforce integer/nonnegative counts or total online limits.
- Vehicle filtering already requires max_passengers_count >= requested passengers; serializer also rejects passenger count above 7.

## Changes in this slice
- Backend lead-time threshold changed from 3h to 24h.
- Backend lead-time comparison now explicitly constructs the pickup datetime in Django's current timezone.
- Corrected the over-eight-suitcase message to describe the luggage limit.
- Quote payload boundary now requires 1–7 passengers, nonnegative integer luggage and <=8 total suitcases.
- First booking screen checks adults/children/infants/luggage as whole nonnegative values before a quote request.
- Existing downstream quote/vehicle/payment state is invalidated only after route/date/time/count validation succeeds and immediately before the fresh quote request.
- Extended isolated quote-helper regression cases for count boundaries.

## Important limits
- No production request, booking, payment or deployment was made.
- Browser/UI, Django suite and full application build still need execution in a suitable checkout/test environment.
- The 24-hour rule must also be exercised at exact boundary, just below/above boundary, midnight and UK DST transitions.
- Server-side validation remains authoritative; frontend validation is user feedback/defence in depth.
- The UI currently permits selecting today's date; this is acceptable only if submit/server validation prevents a <24h quote. A future UX improvement can disable impossible date/time combinations without becoming the authority.
