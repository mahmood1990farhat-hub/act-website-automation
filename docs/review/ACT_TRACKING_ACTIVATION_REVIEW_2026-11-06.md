# ACT tracking activation helper — independent review

Reviewed on 6 November 2026. This is a source review of a prepared activation helper, not a Hostinger execution or deployment receipt. Owner approval is still required before activation.

Reviewed file: `activate_existing_tracking.py`

SHA256: `e22d945f4d7d9ca2fa06f07bd3e5b02746ef7d7c505d227512e241a3bdec81ab`

Prepared source pair:

- Backend: `d77e896af9daca5a39b7a85d5b76c5821e008d23`.
- Website: `3a82c16f1eb648f274759b2567db4fe433720d17`.

## Findings resolved during preparation

1. Candidate cleanup now requires a unique activation marker in the candidate's environment. A concurrent process with the same name and command cannot be deleted merely because its paths match.
2. Recovery checks the original Nginx routing before cleaning up a frontend whose public switch was never attempted. A concurrent routing change therefore stops automatic cleanup.
3. Backend rollback verifies the actual prior service and HTTP response even if the current symlink already points to the old release. Frontend recovery verifies the new authenticated backend before reporting it preserved and ready.
4. The helper ignores terminal hangup, tolerates lost console output and keeps durable private receipts. On timeout or an explicit interruption, it stops its own command process group before beginning recovery.
5. Killing the PM2 client is not treated as proof that a submitted daemon operation has finished. An unacknowledged frontend start followed by an absent candidate produces incomplete-recovery status, retaining the private journal and old public routing. It does not report a successful cleanup.
6. The expected PM2 launch definition is separate from the object supplied to PM2's configuration normalization. Root's existing Git environment is retained for read-only source checks; no trust configuration is changed.

## Confirmed properties

- Exact release SHAs, staged source hashes, build identity, configuration classifications and routing preimages are checked before activation.
- The full PM2 inventory must contain exactly the two recorded retained processes before a mutation. Extra processes cause a refusal; they are never silently omitted from startup state.
- Existing live process identities, launch definitions and environments are preserved. Startup persistence retains both original saved row objects and appends only the new candidate in PM2's expected format.
- The permitted PM2 start operation is restricted to preparing the new loopback candidate. Daemon creation and restart operations are blocked in that client. Recovery deletes only the candidate bearing this activation's marker.
- The anonymous WebSocket probe sends no JWT, coordinates or booking mutation. It requires authorization refusal followed by close code 4403; payloads are not printed or saved.
- A failed backend readiness check can restore the prior backend before GPS testing. Once the authenticated backend passes readiness, a later frontend failure retains it and restores the website with the combined static assets.
- Neither existing frontend is restarted, the database is not restored or migrated, and no payment mode, booking, driver approval, worker or automation configuration is changed.

## Source basis and limitations

Reviewed the staging schema, previous ACT activation/persistence helpers and current [primary PM2 source](https://github.com/Unitech/pm2/tree/master/lib): `Client.js`, `API.js`, `Common.js`, `API/Startup.js`, `God.js` and `God/ForkMode.js`. These establish the callback, preparation, launch-normalization and saved-process formats used by the helper. They are source references, not an assertion that the host's installed PM2 package was newly inspected.

No remaining blocking source-review findings at the recorded helper hash. The separate finite helper checks are recorded by the test reviewer. Real service startup, origin/public routing, authenticated viewers and phone GPS acceptance remain to be observed after explicit owner approval. Existing application test evidence was not repeated for this review.
