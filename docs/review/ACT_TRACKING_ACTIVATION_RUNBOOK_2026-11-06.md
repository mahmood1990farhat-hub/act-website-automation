# ACT tracking release: inactive staging, coordinated activation and recovery

## Status and purpose

Prepared on 6 November 2026 after the owner's phone showed Trip #34 under **Accepted**. This runbook covers only the shared website/backend changes needed for the existing Android driver's next GPS stage. It is not a deployment receipt or permission to activate. Keep the phone at Accepted until coordinated activation and access checks pass.

The exact prepared candidates are below. Backend test execution and the inactive Hostinger staging receipt must succeed before an activation decision. [Backend PR #116](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/116) records its current CI result; [frontend PR #115](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/115) records the 38 focused checks and full build.

| Component | Candidate | Required base |
| --- | --- | --- |
| Backend tracking consumer | `d77e896af9daca5a39b7a85d5b76c5821e008d23` | `82c0b14ad2a71e1ce3d8d1df3527431b698ac461` |
| Website tracking viewers | `3a82c16f1eb648f274759b2567db4fe433720d17` | PR #114 at `0bb77ab75aed11babf37108054c06c27e77ed701`, itself based on serving `892317fcf938fad5fa6cd9a833a79e900dcc4d8f` |
| Android driver | Existing delivered `862f1ea7f3f7f13a46c932fe55c0622735a64b38` | Existing app and retained test signer; no new APK for this release |

The backend keeps the existing driver authentication protocol. The website adds authenticated viewer messages on the existing WebSocket route. Backend and website candidates must be activated together before the journey test. Older website clients may fail to show tracking; they must never receive an anonymous compatibility bypass. Refresh the passenger/admin page after activation.

## Retained deployment facts

These are previous operator evidence and source references. The staging operation must refuse drift before modifying anything; they are not a fresh server-state claim.

| Item | Recorded value |
| --- | --- |
| Backend current and runtime | `/var/www/atg/atg-backend/current` → `/var/www/atg/atg-backend/releases/20261016T-ready-82c0b14/backend` |
| Backend socket | `/run/act.sock` |
| Backend service | `act.service`, working directory `current`; currently recorded user `root` |
| Shared backend configuration | `/var/www/atg/atg-backend/shared/.env`; retain the rotated secret and independent NI key |
| Preserved Python environment provider | `/var/www/atg/atg-backend/releases/20261015T-ready-735c966/backend/.venv` |
| Serving frontend | `/var/www/atg/front-end/releases/20261015-892317f`, loopback `127.0.0.1:3002` |
| Serving frontend PM2 identity | User `act`, name `act-preview-892317f` |
| Older retained frontend | PM2 name `act`, port 3001, `/var/www/atg/front-end/airportandcitytransfer` |
| Existing Node executable | `/home/act/.nvm/versions/node/v24.13.0/bin/node` |
| Existing PM2 CLI | `/home/act/.nvm/versions/node/v24.13.0/lib/node_modules/pm2/bin/pm2` |
| PM2 daemon and startup | `/home/act/.pm2`, existing `pm2-act.service` |
| Serving PM2 restart policy | `autorestart=true`, `restart_delay=3000`, `max_restarts=5`, `min_uptime=10000` |
| Nginx enabled site | `/etc/nginx/sites-enabled/airportandcitytransfer`; preserve its symlink and resolved file metadata |
| Frontend upstream routes | Exactly `/`, `/api/places`, `/api/place-details` → loopback 3002 |
| Backend routes | Existing `/admin`, `/api/`, `/ws/` → `/run/act.sock`; retain TLS, uploaded media and backend static routing |
| Existing Next asset union | `/var/www/atg/front-end/act-static-892317f-cutover` |
| Prior plan | `/root/act-release-backup/cutover-dydysjlc/frontend-switch-892317f/plan.json` |
| Prior activation receipt | Same directory, `activation-z9391_cw/ACTIVATED.json` |
| Prior PM2 recovery record | `/home/act/.pm2/act-persistence-E3FM2z` |

Primary records: [routing snapshot](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98#issuecomment-6205851645), [explicit Node/PM2 path](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98#issuecomment-6267907933), [PM2 persistence](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98#issuecomment-6270273560), [public activation](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98#issuecomment-6270554228), and [final cleanup](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/98#issuecomment-6270774796).

## Reuse the existing operator helpers

The original helpers were recovered and their exact SHA256 values matched the deployment record:

| Helper | SHA256 | Reusable parts |
| --- | --- | --- |
| `prepare_act_frontend_switch.py` | `83bef405b937bb2e13372a4bcb5f70f86a7db93c5772e99ce40a45c0a300c44a` | Collision-checked asset union, alternate Nginx validation master and private plan |
| `activate_act_frontend.py` | `68d50372980af4755e87ef9a886af5008e5b9d2549ea8f84fa2c3f8643cc741e` | Configuration drift guards, atomic resolved-site replacement, origin/public build-and-asset checks, explicit recovery receipts |
| `persist_act_frontend.sh` | `7a53bcbeea606164fcd654b8f1c31ae0494e8619bf46b829d8616ca17ac3dc47` | Existing act-owned PM2 access and preservation of live/saved launch definitions |

They are pinned to the previous release and must not be rerun unchanged. Their old 3001 → 3002 switch, two-process inventory and exact release/plan checks must be deliberately adapted for one new tracking candidate while preserving both existing frontends. The prior approval covered the old SHAs only.

## Inactive staging — one bounded operation

Prepare a separate backend release and a separate frontend build. Do not overwrite either serving release, its dependencies or its build directory. Use a new private staging receipt under `/root/act-release-backup/`; retain the previous activation record unchanged.

1. Under the existing `/run/lock/act-backend-deploy.lock`, verify the two exact candidate Git objects, allowed source diff and unchanged backend requirements/frontend lockfile. Read the existing current target, activation plan and named PM2 definitions privately. Check that the recorded site still resolves to its saved target and matches the prior activated candidate checksum. Compare only relevant metadata; do not request another package/capacity inventory or print environment values.
2. Export the backend subtree into a new destination named for its exact SHA. Reuse the fixed Python environment only after the unchanged requirements comparison. Preserve shared `.env`, media, static and log links and the current Firebase credential arrangement. These are references to existing resources, not permission to rewrite them. Preserve the 735c966 environment provider. Compile the changed consumer and record its hash. This patch has no migration or dependency-install step.
3. Export the frontend subtree into a new act-owned release directory named for its SHA. Use its own build output and locked dependencies. Resolve the existing production configuration privately, with explicit API origin `https://airportandcitytransfer.com`; record Stripe **test** classification and Maps-key presence without printing key values. Refuse placeholders, an unexpected API origin or a live-mode Stripe key. Build once and record source SHA, lock hash and `.next/BUILD_ID`. A local synthetic-provider build is not a substitute for this connected build.
4. Prepare a separate named candidate launch definition for `127.0.0.1:3003` only after that port is found unused. Port 3003 and name `act-tracking-<frontend-short-sha>` are **proposed new resources**, not claims about existing ones. Preserve the exact 3001/3002 processes. The inactive helper does not start this listener or alter PM2; startup and local HTTP readiness are part of the later approved activation.
5. Create a new root-owned, Nginx-readable asset union from the **entire existing union** plus the candidate `.next/static`. Preserve original paths and bytes; refuse symlinks and same-name/different-content collisions. No private release directory is made publicly readable.
6. Prepare exactly two new site files: candidate = the three frontend upstreams 3002 → 3003 plus the Next asset alias; rollback = existing 3002 upstreams plus the **new combined asset union**. Preserve the original current site text too. No other route, header, TLS or media directive changes. Validate both via `nginx -t -c` using a private alternate master/PID path. Do not install either file or reload Nginx during staging.

The staging receipt must include candidate SHAs/paths/build ID, backend source hash, unchanged dependency hashes, configured API origin and provider classifications, new PM2 launch identity, exact resolved Nginx target, original/candidate/rollback checksums and asset manifest. A refusal leaves serving code/routing untouched. The effective configuration and resolved site bytes are the only missing server inputs to generate the final exact diff; collect them inside this operation rather than through another broad diagnostic round.

## Activation after the owner's exact-pair approval

Recheck the staging receipt and all recorded preimages under the release lock. Any drift stops activation. No real-phone location is sent while the pair is changing.

1. Atomically switch backend `current` to the staged tracking backend and restart **only `act.service`**. This consumer-only patch does not change Celery tasks or schema, so repeat worker drains, scheduler stops and migrations are outside scope. Verify socket/HTTP readiness and the exact running source before proceeding. The existing `act.socket` and other services remain in place.
2. Confirm the new consumer fails closed for an unauthenticated transport and still accepts the existing assigned-driver authentication contract using the approved test scenario. Do not change Trip #34 solely to manufacture an active tracking test. Signed-in viewer authorization is accepted with the controlled active booking when that stage is reached.
3. Start only the **new** loopback frontend using the staged launch definition and the root-private captured public-environment file; perform its bounded `/en` build-identity check. Apply the already-recorded bounded restart policy, preserve a private current PM2 dump and save/read back the intended process list with all retained processes. Recheck existing 3001/3002 identities. Do not reinstall PM2, create a new startup service or use `restart all`.
4. Atomically install only the reviewed Nginx candidate at the existing resolved site target, preserving its symlink, owner, mode and extended attributes. Run `nginx -t`, then `systemctl reload nginx.service`. The only public routing changes are the three frontend upstreams and the Next static alias.
5. Verify origin/public HTTPS build identity, one new CSS/JS asset and retained assets, and unchanged existing API route status. Record the source pair as **deployed**, not merged or journey-accepted. Refresh the passenger/admin pages, then start the bounded owner-controlled journey acceptance.

## Recovery

- Before the public reload: restore only changed preimages using drift-checked comparisons. Preserve all new candidates and diagnostics for inspection.
- After a frontend failure: install the prepared **3002 + combined-assets** rollback, validate and reload Nginx, and verify the recorded prior build. Keep the new authenticated backend if it is healthy; an older anonymous viewer fails closed. Do not use the historic 3001 rollback for this release.
- If the backend restart/readiness fails before GPS testing: restore the previous `current` target and restart `act.service`, retaining all data and the rotated configuration. This restores the old viewer-access gap, so the phone remains at Accepted and the GPS test remains blocked. Never report this as a safe-to-track state. If real GPS has already begun, halt that tracking test before a backend rollback; restoring the older consumer must not silently reopen viewer access during an active test.
- Do not restore old databases, secrets, credentials, uploads or payment settings; do not cancel/complete bookings as a deployment recovery action. A concurrent Nginx/current-pointer change is a stop condition, not permission to overwrite another change.

## Exact approval statement to present only after staging succeeds

“Approve activating backend `d77e896af9daca5a39b7a85d5b76c5821e008d23` and website `3a82c16f1eb648f274759b2567db4fe433720d17` for the ACT tracking test: switch the backend release and restart `act.service`, start and persist the new loopback frontend, and reload Nginx with the reviewed three upstream changes and static-asset union. Preserve the current website releases for the documented rollback. This approval changes tracking access and display only; it does not authorize payment-mode changes, booking edits, messages, driver approvals, migrations, automation changes, a new APK or wider driver release.”

The subsequent journey still needs an agreed short route, correct test recipients, phone GPS/heading/navigation-return/connection-recovery checks and matching driver/passenger-web/admin completion. Acceptance of Trip #34 is already evidenced and must not be repeated merely to stage this release.

## Inactive staging helper prepared in this change

`ops/first-journey/stage_existing_tracking.py` implements the staging section with `--prepare --backend-sha FULL40 --frontend-sha FULL40`. It receives exact candidate objects into the existing Git source cache without checking out files or changing refs/FETCH_HEAD. PM2 metadata is read once through passive local RPC, which cannot launch a daemon. It builds only new release directories, preserves the existing resource/configuration arrangements and writes a private staged plan; it does not start an application listener, install live routing, change PM2 state, restart a service or make a provider/booking HTTP request.

The existing dotenv files and captured public PM2 overrides are resolved privately. A separate root-private `frontend-public-environment.json` is retained so later activation uses the same effective public values. Build output is private. The build is not claimed to run in a network-isolated environment; no new operating-system namespace or container prerequisite is imposed.

Twelve finite helper checks passed, including source/archive scope, configuration-mode checks, collision/link refusal, drift refusal, new-directory permissions without following shared links, and passive RPC behavior. Python 3.11 grammar and both embedded Node snippets also passed. These are local helper checks; the helper has not run on Hostinger, and no connected release or actual Nginx validation result is claimed yet.
