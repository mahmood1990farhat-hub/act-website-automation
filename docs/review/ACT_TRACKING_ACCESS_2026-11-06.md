# Existing ACT trip tracking: authorised viewers and fresh locations

## Purpose and status

The owner has shown Trip #34 in the Android app's Accepted list. Before this
phone sends live journey locations, the shared stream must restrict who receives
them. The reported running backend is `82c0b14ad2a71e1ce3d8d1df3527431b698ac461`.
Its consumer subscribes every opened socket and sends cached GPS before any
authentication. Its existing `driver_auth` check protects publication only.

This candidate is based directly on that running backend revision. The sole
application source change is `act_backend-main/apps/trips/consumers.py`.
Website PR #114's configured-origin/socket work is preserved separately; its
viewer integration must be deployed with this backend change. No Android code,
dependency file, database migration, payment, booking, notification setting or
automation workflow is changed here. This document does not approve deployment.

## Existing protocol, now authorised before subscription

- The existing `/ws/trips/{trip_id}/tracking/` path remains in use.
- Opening a WebSocket accepts a transport only. It joins no group and reads no
  cached location until the caller successfully authenticates.
- Existing Android `driver_auth` with `access` (or the retained `token` alias)
  continues to receive `auth_ok`. The added `role: "driver"` field is additive.
- Website viewers send `viewer_auth` with the existing signed-in access token
  and receive `auth_ok` with `role: "viewer"`.
- Viewers are active staff, or active, approved, profile-complete passengers
  with a Passenger profile and ownership matching the existing passenger REST
  relationship/email fallback. An anonymous guest confirmation/PDF token grants
  no stream access. Existing signed-in passengers can still view their guest
  bookings through the existing verified-account email fallback.
- Only the currently assigned, active, approved and profile-complete ACT driver
  may publish. A viewer cannot use `location_update` to publish.
- A failed authentication sends the existing `auth_error` event and closes with
  code 4403. Failed reauthentication clears the previous subscription.

The actual JWT signature/type/expiry validator and current database permissions
are checked again before every publish and location delivery. Suspension,
approval/ownership changes, driver reassignment and non-trackable trip states
therefore block subsequent GPS without relying solely on handshake permissions.
The existing stop service's `ended` event clears the subscription and ends the
socket; queued location callbacks cannot restart it.

## Location freshness and previous assignments

The public location envelope remains
`{type: "location", location: {lat, lng, heading, speed, received_at}}`.
`received_at` is the server's UTC ISO8601 receipt timestamp. It is explicitly not
a claim about when the device obtained its GPS fix: the existing Android GPS-age
and shutdown controls remain necessary and unchanged.

The existing Redis key is reused, with a 30-second expiry. The stored object
binds the location to the publishing driver assignment. Legacy entries without
that binding or a timestamp, expired/future entries, and data from a previous
assignment are withheld. This prevents a retained one-hour cache or delayed
previous-driver update being displayed as current journey progress. Invalid,
non-finite or out-of-range coordinates are ignored, including oversized numeric
inputs. The website must clear its displayed vehicle after the same 30-second
freshness window and after `auth_error`, `ended` or connection loss.

## Focused verification

`apps.trips.tests.test_tracking_access` contains 19 cases using the actual
consumer, existing ASGI URL routing, Django models, JWT validator and a real
isolated database. Only Redis storage is replaced with an in-memory dictionary;
the actual in-memory Channels group implementation delivers events between
communicators. It covers pre-auth cache/group exclusion, permitted roles,
unrelated/invalid/expired callers, read-only viewers, assigned-driver publication,
cache age/assignment, changing permissions, expiry after authentication,
terminal states, existing stop-service shutdown and malformed coordinates.

The dedicated `tracking-viewer-access.yml` runs only this suite on a hosted
Ubuntu runner, Python 3.11 and an isolated PostGIS service. It uses synthetic
credentials, in-memory email/Channels/Celery configuration, no provider secrets,
no live URLs and no self-hosted production runner. It preserves logs even on
failure and records dependency versions/source hashes. Existing dependency
requirements and unrelated completed suites are unchanged.

At drafting, Python 3.11 grammar and diff checks passed locally. The local
container lacks GeoDjango system libraries and its package manager cannot change
user IDs, so no claim of a local real-database test pass is made. The hosted
workflow result is the authoritative execution evidence to attach before this
candidate is considered tested.

## Activation limits

This is not deployed and does not establish phone GPS or complete-journey
acceptance. Deploy the matching viewer integration and backend candidate only
through an owner-approved, concrete cutover/rollback. Until then, remain at the
Accepted phone stage. Old website viewers without `viewer_auth` deliberately
receive no GPS from the protected backend. The new cache format is an internal
change; stop the controlled test's tracking before rollback, and account for its
test-trip cache when reverting to the old backend. No existing release or live
cache was modified during development.
