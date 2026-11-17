# ACT tracking release: inactive staging, coordinated activation and recovery

## Status and purpose

Prepared on 6 November 2026 after the owner's phone showed Trip #34 under **Accepted**. This runbook covers the shared website/backend changes needed for the existing Android driver's next GPS stage. The owner subsequently approved the exact source pair and supplied the successful final Hostinger activation receipt. The pair is now **activated**, with the owner-supplied evidence recorded below. Actual phone GPS and full journey acceptance remain outstanding.

The exact activated application sources are below. All 19 backend CI cases, 38 frontend effect cases and 27 activation-helper cases have passed; their evidence is retained without another application-suite run. [Backend PR #116](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/116) and [frontend PR #115](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/115) remain open, draft and unmerged. Deployment of the approved exact commits is a separate status from merging or accepting the complete journey.

| Component | Candidate | Required base |
| --- | --- | --- |
| Backend tracking consumer | `d77e896af9daca5a39b7a85d5b76c5821e008d23` | `82c0b14ad2a71e1ce3d8d1df3527431b698ac461` |
| Website tracking viewers | `3a82c16f1eb648f274759b2567db4fe433720d17` | PR #114 at `0bb77ab75aed11babf37108054c06c27e77ed701`, itself based on serving `892317fcf938fad5fa6cd9a833a79e900dcc4d8f` |
| Android driver | Existing delivered `862f1ea7f3f7f13a46c932fe55c0622735a64b38` | Existing app and retained test signer; no new APK for this release |

The backend keeps the existing driver authentication protocol. The website adds authenticated viewer messages on the existing WebSocket route. The pair has been activated together. Older website clients may fail to show tracking; they must never receive an anonymous compatibility bypass. Refresh the passenger/admin page before the connected tracking check.

## Pre-activation deployment facts retained for recovery

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

## Exact approval statement subsequently approved by the owner

“Approve activating backend `d77e896af9daca5a39b7a85d5b76c5821e008d23` and website `3a82c16f1eb648f274759b2567db4fe433720d17` for the ACT tracking test: switch the backend release and restart `act.service`, start and persist the new loopback frontend, and reload Nginx with the reviewed three upstream changes and static-asset union. Preserve the current website releases for the documented rollback. This approval changes tracking access and display only; it does not authorize payment-mode changes, booking edits, messages, driver approvals, migrations, automation changes, a new APK or wider driver release.”

The subsequent journey still needs an agreed short route, correct test recipients, phone GPS/heading/navigation-return/connection-recovery checks and matching driver/passenger-web/admin completion. Acceptance of Trip #34 is already evidenced and must not be repeated merely to stage this release.

## Inactive staging helper prepared in this change

`ops/first-journey/stage_existing_tracking.py` implements the staging section with `--prepare --backend-sha FULL40 --frontend-sha FULL40`. It receives exact candidate objects into the existing Git source cache without checking out files or changing refs/FETCH_HEAD. PM2 metadata is read once through passive local RPC, which cannot launch a daemon. It builds only new release directories, preserves the existing resource/configuration arrangements and writes a private staged plan; it does not start an application listener, install live routing, change PM2 state, restart a service or make a provider/booking HTTP request.

The existing dotenv files and captured public PM2 overrides are resolved privately. A separate root-private `frontend-public-environment.json` is retained so later activation uses the same effective public values. Build output is private. The build is not claimed to run in a network-isolated environment; no new operating-system namespace or container prerequisite is imposed.

Twelve finite helper checks passed, including source/archive scope, configuration-mode checks, collision/link refusal, drift refusal, new-directory permissions without following shared links, and passive RPC behavior. Python 3.11 grammar and both embedded Node snippets also passed. The original helper-review JSON preserves the historical prepared-but-not-executed state; the later host result is recorded separately below.

## Owner's successful host preparation receipt — 6 November

The owner's Hostinger screenshot shows `TRACKING RELEASES BUILT AND ROUTING PREPARED - NOT ACTIVATED`, backend `d77e896af9daca5a39b7a85d5b76c5821e008d23`, and frontend `3a82c16f1eb648f274759b2567db4fe433720d17`. The root prompt returned before the terminal displayed `Lost connection to the server`. Preparation had therefore completed; do not rerun the build just because the terminal session subsequently disconnected.

This is owner-supplied evidence, not an independent shell session by the assistant. The helper reaches that sentinel only after the connected frontend build, inactive candidate/rollback Nginx validation, final drift guards and saved `plan.json`. It has not started the new frontend, changed backend `current`, reloaded routing or sent a booking request. The private receipt remains on the host and is the input for the subsequent activation helper. [Sanitised host evidence](evidence/ACT_TRACKING_HOST_STAGING_2026-11-06.json).

At that stage, the next decision was approval of the staged source pair and exact service/routing actions. That approval and the later activation result are recorded below. No new APK, repeated Accept action, or further capacity/package inventory was required by the staging receipt.

## Concrete activation helper

`ops/first-journey/activate_existing_tracking.py` consumes that existing private record with `--activate --record /root/act-release-backup/tracking-stage-<record-suffix>`. The source pair is fixed in the helper. It performs no build and takes no credentials from chat. The operator command must be pinned to the committed helper's SHA256 and issued only after the owner approves the exact pair above.

Before its first live change, the helper checks the staged plan, reviewed source files, current backend, saved frontend build/configuration, both retained PM2 identities, the saved process list, port 3003, routing bytes and combined assets. It captures the current preimages privately and revalidates the prepared routing. These are guards within the approved activation, not another general server inventory or a repeat of the application suites.

The only application service it restarts is `act.service`. Its tokenless WebSocket probe sends `viewer_auth` without an access token to trip ID 0 and requires `auth_error` followed by close code 4403. That refusal happens before any trip lookup; the probe carries no coordinates, does not authenticate, and does not modify a booking. Existing signed-in driver/viewer behavior remains a controlled-journey acceptance check.

The new frontend receives the captured public build configuration and a unique activation marker. The helper guards PM2's start operation against daemon creation or restarting an existing process, appends the new launch definition while preserving the two saved definitions, and read-checks the result. Recovery can remove only the candidate carrying this operation's marker. It then installs the prepared Nginx file at the resolved site target, validates it, reloads Nginx and compares the website build, protected API response and old/new static assets through the origin and public HTTPS routes.

Terminal hangup and closed output do not interrupt the transaction. Each consequential step has a private journal entry before mutation; command timeouts are bounded. An operator interruption requests recovery. A prior activation journal blocks blind reruns, including when the terminal disconnects before the final output is seen. A later result inspection should read that saved journal; do not rebuild or rerun activation to discover its status.

| Final receipt | Meaning and next action |
| --- | --- |
| `ACTIVATED` | Exact website/backend pair passed runtime readiness and routing checks. Refresh the web viewers, then begin the separately controlled phone journey checks. |
| `STOPPED_BEFORE_ACTIVATION` | A guard refused before any live activation action. Review the specific saved result; serving services were not switched by this attempt. |
| `BACKEND_ROLLED_BACK_GPS_BLOCKED` | The new backend did not pass readiness. Previous backend restored; keep the phone test at Accepted. |
| `FRONTEND_ROLLED_BACK_AUTHENTICATED_BACKEND_RETAINED` | Previous website retained/restored, with the healthy new backend kept. The coordinated website/GPS test remains blocked. |
| `RECOVERY_INCOMPLETE` | A recovery check failed or detected a concurrent change. Preserve the journal and current files for targeted review; do not blindly rerun activation or restore data. |

The finished helper's SHA256 is `e22d945f4d7d9ca2fa06f07bd3e5b02746ef7d7c505d227512e241a3bdec81ab`. All **27 focused helper checks passed**, with no failures, errors or skips. Python 3.11 grammar and all four embedded Node syntax checks also passed. The tests exercise actual helper functions and embedded JavaScript using temporary files, simulated services and an isolated JavaScript VM; they do not count as installed-PM2 integration or live activation. [Check evidence](evidence/ACT_TRACKING_ACTIVATION_CHECKS_2026-11-06.json), [test log](evidence/ACT_TRACKING_ACTIVATION_CHECKS_2026-11-06.log), and [independent review](ACT_TRACKING_ACTIVATION_REVIEW_2026-11-06.md).

The helper's preparation and local checks alone do not constitute activation approval or a host execution receipt. The later approval and successful host execution are recorded separately below.

## Owner-approved activation completed — 6 November

The owner explicitly replied **Approve** to activating backend `d77e896af9daca5a39b7a85d5b76c5821e008d23` and website `3a82c16f1eb648f274759b2567db4fe433720d17` with the reviewed service/routing actions. The subsequent Hostinger screenshot shows the pinned helper at commit `9868b8da5194ce901e03c6d937a773e0d26cb18d`, its matching SHA256, successful preimage verification, authenticated-backend readiness, and **`TRACKING BACKEND AND WEBSITE ACTIVATED - JOURNEY ACCEPTANCE NOT YET RUN`**. Both exact application SHAs and the private activation-record path were printed, then the root prompt returned.

This is owner-supplied server evidence. The final helper sentinel follows backend source/readiness checks, tokenless WebSocket refusal, new frontend startup/persistence, preservation of both old frontend processes, reviewed Nginx installation/reload, origin/public build and asset checks, protected API checks, final identity checks and the private `ACTIVATED` receipt. No additional server inventory, repeat activation or rebuild is required by this result. [Sanitised activation evidence](evidence/ACT_TRACKING_HOST_ACTIVATION_2026-11-06.json).

The next task is the existing Android app's On The Way and fresh-location check, starting from the already accepted Trip #34. The deployment helper sent no phone GPS and changed no booking status. Signed-in web tracking, vehicle heading, navigation return, connection recovery and actual completion still need the controlled phone journey. The original long-route booking may support preliminary app checks; it does not replace the agreed short-route completed-journey test. Native passenger/iPhone and full website acceptance remain separate gates.
