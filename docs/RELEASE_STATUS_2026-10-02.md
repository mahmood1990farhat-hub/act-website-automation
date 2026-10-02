# Approved release status — 2 October 2026

Owner approved deployment. PR #69 merged to main at a111eb4767951a6c5b76a87cc9ce3e5ec1525337 (previous main 29de5e0cf4f3a1d3d12944e0b435d0cd7a0476ea).

## Actual production outcome
- Frontend run 37030011356 succeeded. English/Arabic live homepages and published cancellation terms inspected. Approved 24-hour inclusive refund, loss-based late cancellation, 15/60-minute waiting and five-working-day refund initiation wording present. French foundation not merged; only English/Arabic menu shown. Policy publication occurred with this frontend run on 2 October 2026 (after 15:52 UTC and before live observation at approximately 15:55 UTC); historical booking terms remain unchanged.
- Backend run 37030061847 failed and rolled back. New release directory /var/www/atg/atg-backend/releases/20261002T155353Z-a111eb476795 is root:root mode 0750. Scheduler runs as www-data and returned status 200 (working-directory failure). Deployment health check correctly refused acceptance.
- Current symlink restored to /var/www/atg/atg-backend/releases/20260806T221753Z-5e12ad9c393b/backend. act.service confirmed active/running after rollback. act-celery-beat.service remains failed. Scheduled tasks require urgent recovery; do not claim scheduler operational or email/PDF language changes live.
- Read-only diagnosis runs 37030759609 and 37031124431. First obtained service state but journal read lacked sudo authorization. Second confirmed directory modes, rollback target and available sudo commands. DejaVu Sans is installed; synthetic PDF render in deployment environment still not completed.

## Access blocker and recovery
Runner account act has passwordless permission only for deployment helper and service status/is-active commands. Administrative repair/restart requires authenticated server administrator; do not bypass permissions, change service to root or disable health checks.

First recover the scheduler against the restored release with an administrator: systemctl reset-failed act-celery-beat.service; systemctl restart act-celery-beat.service; systemctl is-active act-celery-beat.service. If unsuccessful inspect bounded service logs securely.

Then review /usr/local/sbin/act-backend-deploy and correct creation of release directories so the existing www-data service can traverse/read required application files. Preserve secret-file restrictions; do not recursively chmod all files or expose .env/credentials. Review new release subtree permissions before retrying the exact approved SHA with migrations disabled. Complete service health, synthetic Arabic PDF/logo and read-only live checks before acceptance.

No real bookings, payments, refunds or emails were created. Stripe receipts remain outside verified scope. Diagnostic workflow changes exist only on codex/release-diagnostics-20261002 and are manual-only; they are not merged into production main.
