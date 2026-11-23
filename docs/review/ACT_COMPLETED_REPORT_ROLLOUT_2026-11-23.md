# Approved completed-journey report backend rollout

## Purpose and approval

The owner approved backend PR #120 at `370dc89af105788ef598d0475c1ace20fd05826f`, including `trips.0009_journey_timestamps`, on 23 November 2026. [Approval record](https://github.com/mahmood1990farhat-hub/act-website-automation/pull/120#issuecomment-7101672916).

That application revision remains frozen. The operational helper is maintained separately so its preparation does not change the approved application or repeat the completed application suite. Backend CI run `45167807951` passed 37 tests. The coordinated driver v10 candidate is already compiled, retained-signed and verified; its source passed 96 tests. Neither a new APK build nor changes to the frontend are required for this rollout.

## Established host state

The owner supplied the successful read-only inspection in [the retained evidence](evidence/ACT_JOURNEY_REPORT_HOST_INSPECTION_2026-11-23.json). The current backend is the previously activated d77 release. Its virtual environment is supplied by the retained October 15 release, shared resources resolve correctly, and the Firebase credential exists as a relative file. Trips migrations 0001–0008 are applied and `act.service` is active.

The installed generic deploy helper supports a verified backup, but also creates a new virtual environment and prunes releases. Those operations do not preserve this host's recorded dependencies. The focused helper reuses the resource-preservation and process-readiness patterns from the November 6 staging/activation helpers. It does not run those older, differently pinned helpers.

## Fixed scope

Run `ops/journey_report/deploy_completed_report.py --deploy` as the existing root operator after checking the downloaded helper's published SHA256. It accepts no arbitrary application revision, service or release destination.

- Application: `370dc89af105788ef598d0475c1ace20fd05826f`.
- Expected previous application: `d77e896af9daca5a39b7a85d5b76c5821e008d23`.
- Candidate: `/var/www/atg/atg-backend/releases/20261123-report-370dc89/backend`.
- Private receipt and backup: `/root/act-release-backup/completed-report-370dc89`.
- Retained environment: `/var/www/atg/atg-backend/releases/20261015T-ready-735c966/backend/.venv`.
- Schema change: only `trips.0009_journey_timestamps`.
- Service restarted for activation or recovery: only `act.service`.

The current frontend, including the separate November 23 admin-header update, is preserved. There is no PM2, Nginx, Celery, n8n, payment, email, driver assignment or trip-action operation. All existing releases and shared resources are retained.

## Execution and recovery

The helper verifies source identities and the recorded resource arrangement, exports the approved backend into a separate release, and preserves the existing virtual environment, shared links, and Firebase file bytes/ownership/mode. It checks the real database migration plan and refuses unrelated pending migrations or schema/history disagreement.

Before schema execution it makes a private custom-format PostgreSQL backup, checks its archive directory, reads the full archive into `/dev/null` without restoring it, and records its byte count and checksum. Migration 0009 executes transactionally before the current-release pointer changes. The pointer switch is atomic, and the running process directory, protected API responses, database schema, Trip #37 invariants and read-only report serialization are checked before success is recorded.

The receipt is durable and reconciled on a retry. A failure before activation leaves the previous code serving. An activation failure restores the previous application pointer and restarts `act.service` while retaining the additive nullable columns. No database restore is performed over live data. An already verified deployment is inspected without another migration or restart.

An unexpected source, resource or current-pointer change stops the operation for inspection instead of overwriting concurrent work. Detailed command output remains in the private host record; do not post the contents of that directory or a database dump publicly.

Successful terminal marker:

```text
COMPLETED_REPORT_BACKEND_DEPLOYED_VERIFIED
```

This marker is host execution evidence only after the owner supplies it. Preparation, local checks and the draft operational PR do not establish deployment.

## Report acceptance

Trip #37 remains completed, paid and assigned with one driver earning and one company revenue entry. Its historical start/end times were not recorded; this rollout does not manufacture them. The legacy report must show unavailable actual timing, and a fresh controlled journey after activation is needed to accept actual start/completion timestamps in the phone app.

After verified backend activation, update-install the already prepared signed v10 APK using Windows CMD and the retained SHA256. Keep application installation and fresh-journey phone acceptance distinct from this backend rollout.

## Validation

**All 18 focused offline operational tests passed** against the final helper. [Machine-readable validation](evidence/ACT_COMPLETED_REPORT_ROLLOUT_OFFLINE_2026-11-23.json) and [test output](evidence/ACT_COMPLETED_REPORT_ROLLOUT_OFFLINE_2026-11-23.txt) record the exact file identities. The helper and its embedded database task also parse under Python 3.11 grammar.

Final helper SHA256: `f78f138ec818c5c67988fe4956df137330519c6e867d9d04a2b9d13a78332b82`.

The cases exercise real orchestration, source hashes, filesystem staging, permissions, durable receipts, backup hashes and atomic pointer changes in temporary directories. Git, database, HTTP, ownership and service adapters are synthetic, and a guard rejects any escaped subprocess. They cover source/schema drift, inaccessible files, failed or changed backups, migration ordering, activation failure, interrupted staging/migration/activation, preservation of accepted receipts, and auxiliary logging failures. Operator interruption is not swallowed by ordinary command logging.

Independent source review and root review of the final logging/interruption changes are complete. These local checks used no host access, production credentials, live database or provider calls. They supplement the existing application CI evidence; they do not replace host execution or fresh journey acceptance.
