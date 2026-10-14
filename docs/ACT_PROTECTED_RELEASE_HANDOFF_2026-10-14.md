# ACT protected unified-onboarding release handoff — 14 October 2026

**HOLD until all release evidence is recorded.** This is a proposed operating procedure, not permission to merge, migrate, provision production secrets, deploy, restart services or execute n8n. It replaces the older 0004/0005-only release plan. Use final exact SHAs and CI evidence from PR #96/#97 comments; never deploy a moving branch or unrelated main.

## Preserved baseline and completed preparation

Accepted production backend: `dc1df73122aafba9d818f9059cd11c17a621405c`. Accepted frontend: `4ef5418408cbd3ef7f1027763963aca4ed02354e`. Original tested PR #94/#95 remain unchanged.

Owner screenshots already verified the live backend manifest, deployment helper, accepted frontend source, and raw driver migration history 0001–0003 only. The owner authorised/executed private directory creation at `/var/www/atg/atg-backend/shared/private_driver_documents` with www-data/0700 and added `ACT_DRIVER_PRIVATE_UPLOAD_ROOT` to protected shared `.env`. The displayed literal Nginx root/alias list did not point to the private directory. No service restart or onboarding deployment followed. Do not repeat completed checks without relevant drift, or loosen `.env` permissions for an unprivileged diagnostic shell.

Trip #34 has already been paid and confirmed. Do not create another booking, replay payments/emails, approve real drivers, reassign trips or alter published workflows during preparation. Passenger/driver apps remain after full website acceptance.

## Application acceptance and known tool restriction

Final exact-pair evidence must cover alternate account suspension/restore, permanent cessation, concurrent assignment locking, private vehicle-history replacement, preserved legacy identity/assignment behaviour, confidential NI access, frontend build and mobile browser/mail/admin acceptance. Only affected tests should be repeated after changes; no real payment provider run belongs to this gate.

A proposed admin-detail correction (include `user.is_active` in `is_currently_available`, and add a response cache policy) was blocked by connector safety enforcement. It was not applied and must not be treated as fixed; no alternate write route was used. Server-side protected operations validate actual state independently. Authorised disposition of that remaining presentation/cache item is required before claiming the entire release complete.

## Production key and recoverability

Generate a new Fernet key **on the VPS** and install `ACT_NI_ENCRYPTION_KEY` through an authorised operator session, preserving all existing environment entries and file permissions. Never use the public CI key, reuse Django SECRET_KEY, print the key, place it in shell history/GitHub, or silently replace an existing key. First save a protected recoverable environment copy. A present key must be validated privately, not regenerated.

Keep the key in an independently controlled encrypted off-host recovery store; a duplicate on the VPS is not disaster recovery. Verify a synthetic encrypt/decrypt round trip using the saved recovery key without revealing it or NI. Record pass/fail and opaque recovery references only. The implementation is single-key: future rotation requires a reviewed re-encryption/version plan, not automatic regeneration. Host key installation and off-host recovery are **not yet evidenced**.

## Database/file backup and exact migration gate

In the approved release window, obtain a fresh consistent PostgreSQL custom-format dump, checksum, schema/version metadata and protected file/configuration backups. Use an exported snapshot or equivalent consistent verification so row counts and the private Trip #34 fingerprint refer to the same snapshot. Keep existing payment/confirmation workers and traffic unchanged while preparing.

Restore the archive into a **new isolated disposable database**, never production. Require successful restoration plus critical row/migration/Trip #34 state verification. Do not start email, Celery, n8n, dispatch or provider jobs against the copy. `pg_restore --list` and `pg_restore --file /dev/null` are readability checks, not a successful database restoration. Clean up only the exact disposable database after verification. Store encrypted off-host copies and verify recovered bytes/checksums. The owner must nominate the destination and access; these cannot be invented or inferred from the local backup directory.

Candidate driver migrations are **0004, 0005, 0006 and 0007**. Inspect the entire candidate migration plan against real production outside the live code directory. Abort if any additional app migration, incompatible starting state or failed recovery check appears. Never run makemigrations/fake/reverse operations in production. Obtain explicit approval naming final SHAs, this migration set, recovery references and release window before applying them.

## Protected backend → frontend activation and rollback

Stage the approved backend subtree separately, retain shared env/media/static/private evidence, and pin the known-good release against pruning. After successful recovery/plan gates and release approval, use the reviewed backend helper and check health before any frontend activation. Do not start previously stopped schedulers, replay queues or change n8n. The helper intentionally does not auto-rollback after migrations.

Do **not** dispatch existing `deploy-frontend.yml` for this off-main release: it is pinned to a different historic SHA. Build the exact candidate in a separate directory with preserved production public API/environment settings and locked dependencies before touching live files. Preserve the existing coherent build, CSS, env and PM2 configuration. The operator must record actual PM2 user/cwd/command/port and Nginx upstream/static paths privately, then validate one compatible atomic release-symlink or side-by-side-upstream activation and rollback method. Do not assume live is already a symlink or use blind rsync --delete/in-place builds. Attach exact chosen paths/health/rollback commands to release approval; no live topology change is authorised by this document.

If frontend activation fails, restore the accepted frontend build/config and retain compatible new backend/schema. After backend migrations, prefer supervised forward repair or reviewed compatible code rollback retaining database/uploads/key. Never restore an old whole database over later paid bookings or reverse 0004–0007 to discard applications. Whole-database restoration requires write control and reconciliation of all newer transactions.

## Proposed retention operating arrangement — owner acceptance required

A named ACT reviewer should operate a retention register; no new automated deletion workflow is authorised. Required driver operator records are retained while available and for the required 12 months after actual cessation. Each vehicle/keeper period has its own post-cessation retention; replacement must not overwrite the old period. At expiry, review documented lawful holds and dispose/anonymise data no longer needed. Temporary account suspension does not fabricate a permanent cessation date.

DBS and other intrusive vetting originals are not automatically entitled to blanket 12-month/indefinite storage. Keep the necessary verification result and securely destroy unneeded vetting material as soon as reasonably practicable unless another documented lawful requirement applies. Assign rejected/abandoned applications an explicit purpose-based expiry/review. Include admin downloads, backups and restore procedures in disposition policy; do not copy NI/evidence into logs/profilers/GitHub. No existing records may be deleted under this task without a specific approved disposition.

Official sources reviewed: [TfL Operator Handbook](https://content.tfl.gov.uk/private-hire-operator-handbook.pdf), [ICO vetting guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/employment/recruitment-and-selection/pre-employment-vetting-of-candidates/), [PostgreSQL pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html). This operating proposal is not a claim that a purge service is installed or that legal compliance is certified.

## Automation coordination and final closure

Handoff: [act-ai-workflows issue #1](https://github.com/mahmood1990farhat-hub/act-ai-workflows/issues/1). Django owns the new flow/emails; no new n8n publisher or duplicate communications. Historical final_approved alone is not current driver eligibility. The automation owner must acknowledge whether consumers are unaffected or need a separately approved adapter. Issue creation is not acknowledgment. Published workflows and Support case 16642348's affected connection/workflow stay unchanged.

Final release record requires: exact-pair CI success; resolution of the blocked detail item; actual host key and independent encrypted off-host recovery proof; fresh successful DB restore; full production migration plan; accepted retention and automation disposition; validated frontend activation/recovery commands; and explicit release approval. Preparing this handoff executes none of those production operations.
