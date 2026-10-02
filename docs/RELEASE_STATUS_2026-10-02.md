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

## Acceptance completed
The owner executed the immutable acceptance helper and reported all five offline language tests passing and both Arabic PDF renders successful. Synthetic output directory: /tmp/act-language-check-a111eb476795-794ce1bc.
Retrieval run 37039077593, job 110944450415, succeeded on 2 October 2026 after validating the manifest, deployed SHA, file lengths and SHA-256 digests. It also confirmed both application and scheduler still active, approximately twenty minutes after deployment.
- Booking PDF: 71,929 bytes; SHA-256 5ff4df8b199db668a9c268c2c99dc8d819b232f7ac3a9226954355f34ba6176e.
- Cancellation PDF: 72,448 bytes; SHA-256 934cb5cc2021c0fcdbc1446ed4da91e3731a9f391d7a24c4c0870a5056bea120.
- Both PDFs contain one page, embedded DejaVu Sans regular/bold fonts and one logo image.
- Both were rendered with Poppler and visually inspected: Arabic glyph shaping and right-to-left layout readable; logo top-left; rows, totals, contact information and footer within page bounds; no clipping or overlap observed.
- The five offline tests exercised deployed booking-owned email language paths with sends substituted, legacy language fallback, template escaping, refund-status copy and English vehicle registration. They do not constitute actual email delivery or full payment/webhook integration tests.

The approved English/Arabic frontend and backend release is deployed and its bounded acceptance checks are complete. No further owner terminal action is required for this release.

## Scope and limitations
No real bookings, payments, refunds or outgoing emails were created. Stripe receipts and full database/webhook/payment integration remain outside verified scope. Existing stored customer PDFs were not regenerated. Deployment logs still show a missing Firebase credential-file warning; Django checks pass, but Firebase-dependent features were not verified.
Diagnostic workflow, source repair and acceptance helper changes exist only on codex/release-diagnostics-20261002; they are not merged into main and do not deploy another application version.
