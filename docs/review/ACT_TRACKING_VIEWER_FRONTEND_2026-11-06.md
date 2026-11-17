# Existing website tracking: authorised viewers and honest location state

## Scope and baseline

This frontend candidate builds on website PR #114 at `0bb77ab75aed11babf37108054c06c27e77ed701`. That existing origin and cleanup work remains intact. Five application files and the existing tracking effect test file change. No native app rebuild, new tracking system, dependency change, checkout change or provider configuration change is needed for this patch.

The owner has supplied phone evidence that Trip #34 reached **Accepted** on 6 November 2026 at 11:53 London. This patch prepares the later passenger/admin website tracking stage; it does not establish GPS or full journey acceptance.

## Resulting behaviour

- Passenger and admin trip details pass their existing sign-in token and locale into the existing tracking map. A missing token opens no socket.
- The existing `useTripTracking` hook owns the socket and sends `viewer_auth` with the access token in a message. Tokens are never added to the URL or logged. Opening a transport does not grant access; only `auth_ok` with the viewer role enables location consumption.
- The existing map provider consumes that hook and preserves its interpolation, heading and camera effect. The route remains visible while waiting. A vehicle marker appears only after an authorised, valid recent position; the route's first point is no longer presented as the driver.
- The matching backend supplies `location.received_at` in UTC. Positions with no receipt timestamp, invalid coordinates, receipt age of 30 seconds or more, or more than five seconds of future clock skew are ignored. A timer removes the displayed driver position when its remaining 30-second receipt lifetime expires. A fresh update can restore it on the same authorised socket.
- The receipt timestamp measures when the server received a position. The existing driver app separately rejects stale GPS measurements before publishing. Receipt age is not independent proof of measurement accuracy or age.
- Refused authentication, completion, cancellation, a disconnected socket and an expired position clear the animation target and vehicle marker. Late frames cannot restore a stopped session. Token/trip changes dispose of the prior socket and timers.
- Plain English/Arabic messages distinguish connection, waiting, live, old location, access refusal, completion, cancellation and disconnection. A disconnected browser asks the user to reopen the trip. No automatic retry or new reconnect system is introduced.
- A synchronous browser transport failure is handled without breaking the map. If viewer authentication is not acknowledged within 15 seconds, the connection closes with an unavailable state. Terminal completion/cancellation messages remain visible after close.

## Verification

The actual source passed **38 focused effect checks**: the 17 affected existing tracking cases and 21 authentication, freshness, terminal-state and failure cases. WebSocket, Maps, clock and animation surfaces are controlled doubles. The separate unchanged URL helper's 12 unit cases were not repeated.

The full Next.js 16.1.6 build passed compilation, TypeScript, page-data collection and static generation with Node 24.22.1 and the unchanged dependency lock. The API origin was `https://airportandcitytransfer.com`; Maps/Stripe values were synthetic build placeholders. The existing middleware-filename deprecation warning remains. This is source/build evidence, not a deployable provider-configured release or connected browser acceptance.

Final review then clarified one socket comment and added `minHeight: "300px"` directly to the map container so its percentage height cannot collapse. No logic, dependency or test changed after the successful checks. These two small edits were reviewed without repeating the suite/build; the evidence records both the checked and final source hashes.

See the adjacent [machine-readable evidence](evidence/ACT_TRACKING_VIEWER_FRONTEND_2026-11-06.json) and [full build log](evidence/ACT_TRACKING_VIEWER_FRONTEND_2026-11-06-build.log).

## Coordinated activation and remaining acceptance

This frontend requires the matching backend repair: the same tracking route must defer group subscription and cached location delivery until an authorised driver or viewer authenticates, and must supply `received_at` on location envelopes. The existing Android `driver_auth` protocol is preserved.

The website list and selected trip's surrounding status still follow their existing data refresh behaviour; the map itself handles terminal events immediately. Connected acceptance must confirm the same booking and final status in driver, passenger web and admin, including a refreshed authoritative trip record.

No deployment, live record change, GPS publication, booking, payment or message was performed. Preserve the existing releases and Trip #34. Connected activation requires owner approval and the existing public-provider configuration, followed by the agreed controlled short-route journey. Guest unauthenticated tracking, passenger-native/iPhone acceptance and wider website release acceptance are outside this patch.
