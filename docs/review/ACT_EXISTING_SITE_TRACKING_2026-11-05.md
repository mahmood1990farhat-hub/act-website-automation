# Existing ACT website tracking candidate — 5 November 2026

## Purpose and source

The serving website source still directs journey tracking to the older `act-backend.horizontechco.com` host. This candidate reuses the preserved configured-backend tracking correction on the exact serving frontend base, so the existing website and Android driver can participate in the agreed controlled journey.

- Repository: `mahmood1990farhat-hub/act-website-automation`.
- Candidate branch: `draft/act-existing-site-tracking-20261105`.
- Exact base: `892317fcf938fad5fa6cd9a833a79e900dcc4d8f`, the head of [frontend PR #97](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/97).
- Application and retained-test source published at `fb34b518649212986168249ca65cf2cfa416df61`. Subsequent changes on this branch are review evidence and a read-only host diagnostic; compare the four application-file hashes below when evaluating a later documentation-only revision.
- Preserved implementation: local commits `b9978299c341e9bba12300784ee021a736f8cfc7` and `eac39979bbfd669feec5354e43c9f36912588050`.
- Existing backend: `82c0b14ad2a71e1ce3d8d1df3527431b698ac461`, [backend PR #98](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98).
- Existing driver candidate: `b673061e3c0ce47ee96689312c03bfa1c0ad5b22`, [driver PR #14](https://github.com/mahmood1990farhat-hub/act-driver-app/pull/14), open/draft/unmerged.

GitHub heads were re-read on 5 November before source preparation. The original tracking publication path previously stalled; the branch and contents API succeeded during this continuation. The new candidate is remotely committed, not merged or deployed. No production workflow has been dispatched.

## Four application changes

| File under `act_website-main/` | Result |
| --- | --- |
| `src/lib/trip-tracking-url.ts` | Derives the existing root WebSocket route from the explicit absolute REST API configuration; rejects missing or malformed configuration rather than using an old default host. |
| `src/components/_components/dashboard/tracking/trip-tracking-provider.tsx` | Reuses the configured origin and the preserved owned-socket cleanup, trip-change reset and late-callback guards. |
| `src/hooks/use-trip-tracking.ts` | Carries forward the same configured-origin and lifecycle correction for the retained hook. |
| `src/components/_components/dashboard/TripsDashboard.tsx` | Keeps the live map visible for `active` and `driver_on_the_way`, matching the existing backend status names. |

All four files exactly match the preserved implementation. The package manifest, lockfile, TypeScript configuration, backend, checkout, pricing, policy, provider integrations and native app are unchanged. The two existing tracking tests are preserved alongside the candidate; their behavior was not rewritten.

## Host evidence supplied by the owner

The owner ran the read-only release diagnostic and pasted its completed output. Its terminal echo was visually garbled, but the output reached `READ_ONLY_COMPLETE` and reported:

- Both the current backend target and running process directory resolve to `/var/www/atg/atg-backend/releases/20261016T-ready-82c0b14/backend` with release receipt `82c0b14ad2a71e1ce3d8d1df3527431b698ac461`.
- The configured backend file contains a test-mode Stripe key. This is a mode classification, not disclosure of the key or proof of a running process's loaded value.
- Port 3002 serves `/var/www/atg/front-end/releases/20261015-892317f`; the Nginx inspection references port 3002.
- The old port-3001 instance remains present. It and all old releases/backups must be preserved.
- The provider/hook source SHA256 values exactly match the deployed Git preimages below. Build-ID fingerprints establish identities but do not prove embedded API/payment configuration.

The existing website is dormant and deliberately uses Stripe test mode, according to the owner. The existing test webhook pointing to this same website/backend is expected for that arrangement. A second environment and separate Stripe sandbox remain optional, not prerequisites imposed by this patch.

| File | Serving/preimage SHA256 | Candidate SHA256 |
| --- | --- | --- |
| `src/lib/trip-tracking-url.ts` | Absent in base | `77bd9c2f08318dc97e2eac70003f67f791294c204ee4cc9225ffb2bbf5327c56` |
| `src/components/_components/dashboard/tracking/trip-tracking-provider.tsx` | `cecbdb13f4eb8a8dc59d48e6b8e887a0e597bb6690abe7310d5592328975e05e` | `417d7f0deb09770863358c491d92a1dcbf5a053e5142fc7183af876235f1eef0` |
| `src/hooks/use-trip-tracking.ts` | `9fc22c77e5677c0820f124b3d3cc8fd5f16ed0dea8cbf16a1f9487cf1b8317ec` | `28ed2eb8fa1fab9477c0fe05a1cad64cd6c90a9c99ac2dde75ee3edb1e479e74` |
| `src/components/_components/dashboard/TripsDashboard.tsx` | `02446b2a772eeaf4b5535b5cd682a7e784b85b885e09c61dc9c56365cbc0d377` (Git base; not collected from VPS) | `6df832db2bce8bec932111453202c5a61342d9df01b3a727e9d9c64e13c65714` |

## Verification completed

1. Fetched the exact serving Git commit into an isolated local worktree and compared all selected files and dependencies with the original tested tracking base `4e469cf93327d89d7e28a09cd8ef3cc96b011f8a`. The three existing target files, package manifest, lockfile and TypeScript configuration are identical before applying the preserved changes.
2. Confirmed that the relevant backend consumer, WebSocket route, tracking-stop service, ASGI/settings/dependencies and start/complete/on-the-way handlers are identical between serving `82c0b14` and later backend candidate `c317a27`. These four frontend changes need no backend code upgrade.
3. Installed the unchanged lockfile with `npm ci --ignore-scripts --no-audit --no-fund` and ran a full `next build` using Node `24.22.1`, npm `11.9.0`, and the lockfile's Next.js `16.1.6`. Compilation, TypeScript, page-data collection and static generation passed. The existing middleware-deprecation warning remains; it was not treated as a reason to rewrite routing.
4. Built with explicit API origin `https://airportandcitytransfer.com` and synthetic Maps/Stripe placeholders. The compiled quote endpoint has that origin. This is code/build verification, not a deployable connected release or provider acceptance. No browser/native run was performed. A network namespace was unavailable; no claim of network-isolated build execution is made.
5. Reused the retained 12 URL and 17 actual-source effect checks by exact source/test/lockfile hashes. Those 29 checks were not unnecessarily rerun. They use controlled doubles and do not exercise real sockets, GPS, Maps, payments or journey completion.
6. Compared every remotely published application/test file with the locally built candidate and verified the branch changed exactly the four application files plus two retained tests before evidence files were added.

The driver's separate 39-check result remains [run 40702356649](https://github.com/mahmood1990farhat-hub/act-driver-app/actions/runs/40702356649). No driver suite was repeated and no APK was produced during this website-source step.

## Necessary environment and acceptance checks

The next focused host diagnostic must establish the current frontend build configuration, the route to `/ws/trips/`, and the existing PM2/Nginx activation metadata. It must report mode/presence classifications only and must not print provider keys. An absolute `NEXT_PUBLIC_API_BASE_URL=https://airportandcitytransfer.com` is required for the new build; app REST endpoints already include `/api`, so the base must not add another `/api` suffix.

There are existing behaviors that this narrow source reuse does not establish as accepted:

- The map provider does not react to backend `ended` messages by refreshing the selected booking. Record final status before and after refresh separately; a refreshed matching status is not automatic live-status acceptance.
- The browser socket has no reconnect loop. The agreed brief Android-phone connection-loss test must be distinguished from disconnecting the passenger browser.
- The website has no stale-location warning, and the current backend cache has no freshness timestamp. The driver's committed stale-GPS safeguards do not establish website freshness behavior.
- At source level the current WebSocket consumer admits viewers of an active trip before authenticating them; driver publishing is separately authenticated. Nginx access controls/exposure remain unverified. Before sending real phone GPS, establish authorized viewer access or correct that permission gap. Merely opening a socket is not an access-control pass.
- The unused legacy `TripGoogleMap` hook expects a different payload shape. The active passenger/admin path uses the nested-location map provider. Preserve that distinction when recording results.

These observations must be resolved or explicitly exercised in the controlled acceptance work, according to whether they block the agreed journey. They are not reasons to declare a test passed without evidence.

## Concrete build and activation boundary

Prepare a new inactive release directory from the exact reviewed commit and the existing verified public configuration. Use its own dependencies/build directory and record the source, lockfile, build ID, API origin, Stripe mode and Maps-presence classifications. Preserve the currently serving release on 3002, the older 3001 process, static-asset union, PM2 boot state, encrypted backups and Trip #34.

Do not dispatch the current `deploy-frontend.yml`: its main-ancestor restriction, destructive synchronization into the old retained directory and PM2 target do not match this release layout. After reading actual activation metadata, prepare the explicit Nginx/PM2 cutover and rollback to the current 3002 release for the owner's approval. No approval to activate is implied by preparing or reviewing this candidate.

Then verify test accounts/notification recipients and existing Maps/native configuration; build the existing driver candidate, obtain installation approval, and run the agreed website booking through assignment, pickup, tracking and completion. Confirm the same booking, final status, tracking stop and no duplicate charge/booking. Passenger-native, iPhone and full website acceptance remain separate gates.
