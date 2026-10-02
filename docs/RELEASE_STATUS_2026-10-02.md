# Approved release status — 2 October 2026

Owner approved deployment. PR #69 merged to main at a111eb4767951a6c5b76a87cc9ce3e5ec1525337 (previous main 29de5e0cf4f3a1d3d12944e0b435d0cd7a0476ea).

## Production outcome
- Frontend run 37030011356 succeeded. English/Arabic live homepages and published cancellation terms inspected. Approved inclusive 24-hour refund, loss-based late cancellation, 15/60-minute waiting and five-working-day refund initiation wording present. French remains hidden. Policy publication occurred during the frontend run on 2 October 2026, between 15:52 and approximately 15:55 UTC. Historical booking terms remain unchanged.
- Backend retry run 37036634112 succeeded. Deployment success logged at 16:52:43 UTC (17:52:43 London). Active release: /var/www/atg/atg-backend/releases/20261002T165126Z-a111eb476795/backend.
- Both act.service and act-celery-beat.service passed post-restart active checks. Django check passed; no model changes or planned migrations; migrations were disabled. Public login endpoint returned expected HTTP 405 for GET; application socket responded. This is readiness evidence, not an end-to-end booking/payment test.
- Subsequent verification run 37037619819 confirmed both services still active at 17:00 UTC. Its document step was blocked at directory traversal because the runner account act is not in www-data; this did not affect the successful deployment.
- Live English terms and Arabic booking form reviewed again after deployment. Arabic airport marketing cards remain English outside this focused release scope.

## Permissions repair
Initial backend run 37030061847 rolled back because newly created release and virtual environment directories were root:root mode 0750, blocking the www-data scheduler (status 200/CHDIR).
The owner recovered the scheduler and, at approximately 16:47 UTC, successfully patched /usr/local/sbin/act-backend-deploy. Backup: /usr/local/sbin/act-backend-deploy.bak-1790959659.
After existing ownership/write restrictions and before the release switch, the helper now assigns www-data group to the release root/backend directory and virtual environment, then checks Celery/WeasyPrint imports as www-data. No broad chmod or health-check bypass. The source helper on this diagnostic branch records the same correction.

## Remaining acceptance check
DejaVu Sans was confirmed installed in earlier run 37031124431. A synthetic Arabic booking and cancellation PDF render on the deployed environment remains pending.
The automation account cannot traverse the protected release. Do not widen its permissions. Administrator execution of server/deploy/verify-customer-documents.py at immutable commit b1c0edec6c97b0df1210841f5205e8a90d3afd25 verifies the deployed SHA, runs the five existing offline tests and the deployed Arabic PDF functions with isolated Django template settings. It reads no production secrets, queries no database, sends no messages and makes no payments. It writes only synthetic PDFs and a manifest to a new /tmp/act-language-check-a111eb476795-* directory readable by the existing runner for subsequent visual inspection. No production permissions are modified.
Once the owner provides the output directory, retrieve only those synthetic outputs through the diagnostic workflow, render and visually inspect both PDFs, then update this checkpoint. Do not claim server PDF acceptance before this completes.

## Scope and limitations
No real bookings, payments, refunds or outgoing emails were created. Stripe receipts and full database/webhook/payment integration remain outside verified scope. Existing stored customer PDFs were not regenerated. Deployment logs still show a missing Firebase credential-file warning; Django checks pass, but Firebase-dependent features were not verified.
Diagnostic workflow, source repair and acceptance helper changes exist only on codex/release-diagnostics-20261002; they are not merged into main and do not deploy another application version.
