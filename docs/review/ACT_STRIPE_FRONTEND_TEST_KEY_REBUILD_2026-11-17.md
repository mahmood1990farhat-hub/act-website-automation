# ACT Stripe test publishable-key repair — frontend-only candidate preparation

Date: 17 November 2026. Workstream: website/backend; PR #115 (frontend), related PR #117 (backend Stripe incident). This record authorises **no production operation**.

## Evidence and root cause

1. The owner replaced the expired backend **test secret** with approval, restarted only act.service, and observed normal protected-endpoint HTTP 401. Guest initiation then created an unpaid GBP 5.44 PaymentIntent.
2. The connected ACT test account verified that existing PaymentIntent had status requires_payment_method, amount_received 0, and no payment method or charge.
3. The owner executed the SHA-256-verified read-only key diagnostic: the **historically captured** frontend test publishable key could not retrieve that intent. Exact Stripe error: HTTP 401; type api_error; code api_key_expired.
4. A separate owner VPS read-only check returned:
   - NGINX_ROUTING_MATCH: True
   - ACTIVE_PROCESS_MATCH: True
   - COMPILED_STRIPE_KEY: MATCHES_EXPIRED_CAPTURE
   - NO_CHANGES
5. The owner then entered a current **replacement pk_test_ key** privately at the Hostinger root terminal. A read-only GET of the existing unpaid intent returned PASS: REPLACEMENT_TEST_PUBLIC_KEY_VALID; NO_CHANGES. The key was neither saved in chat nor changed in the frontend.

Conclusion: the active frontend is built with the expired test publishable key. The replacement key works against the existing ACT test PaymentIntent. No source-level Stripe checkout rewrite is justified.

## Pinned preservation boundary

- Accepted **application** frontend source: 02e59f95b5fd85d6ad07e881f3f2671a01a7bd65, existing passenger PR #115. This is distinct from the later documentation/release-helper commits.
- Accepted backend source: d77e896af9daca5a39b7a85d5b76c5821e008d23, separate PR #116.
- Current frontend process: port 3004, release passenger-02e59f9-eoszulb3; existing static union act-static-passenger-02e59f9-eoszulb3.
- No backend, checkout logic, PaymentIntent, webhook, tracking, driver/Android, n8n, pricing or cancellation change.
- Do not remove any branch, source, static asset or existing PM2 process. The current process/assets are the preserved rollback state.

## Source-only work completed on PR #115

- ops/payments/prepare_stripe_frontend_candidate.py — a conservative operator tool with **--check** (read-only) and **--prepare** (build an INACTIVE new release). It has NO activation/switch action.
- ops/payments/test_prepare_stripe_frontend_candidate.py — 12 isolated, synthetic safety tests.
- Source and test Git blobs match the byte-for-byte files on which the local 12-test Python unittest run passed; no CI, hosted frontend build or VPS execution has yet been claimed.

The tool requires the exact existing release/Git commit, current Nginx/3004 process, backend pointer, private prior public-configuration receipt, old compiled key and backend environment. It checks for an existing candidate or release lock and stops on drift. The replacement test publishable key is entered into a hidden prompt, re-verified against the same existing unpaid PaymentIntent using only Stripe GET, never echoed or put into a CLI argument. It is injected only into the new build's process environment. The tool builds fresh source from the accepted SHA, reuses current other public build variables, verifies the candidate's compiled JS has **only** the new key, prepares a separate union of old+new static assets (rejecting conflicting paths), records hashes and a private build receipt, and leaves existing services/routes untouched. New paths are never overwritten, even after partial failure.

**Note:** The tool is guarded but not tested on the live host; environmental differences, disk space, lock availability, dependency install or build failure may stop it. A failed partial candidate is retained for review; do not rerun blindly or delete historical work.

## Safe execution boundaries

A read-only source/environment check can be run from a SHA-256-verified pinned script after reviewing GitHub. A separate owner decision is required before running **--prepare** on the VPS: although it does not switch live traffic, it creates directories and builds npm/Next on the host. In that operation, the user would need to re-enter the private replacement key in the interactive terminal because the earlier key was deliberately not persisted by the diagnostic. Never paste either Stripe key into chat, a shell command, GitHub, a screenshot or a ticket.

The **--prepare** operation does not start an additional PM2 process, reload Nginx, change current environment files, activate a payment, restart act.service, create bookings, run migrations or merge PRs. Do not run it before explicit owner staging approval.

## Approval-dependent activation design — NOT IMPLEMENTED OR APPROVED

After a successful recorded inactive build, prepare a separately reviewed **frontend-only** switch helper (not a manual unguarded edit):

1. Re-read the private candidate receipt and current source/process/Nginx/PM2/backend snapshots; fail closed on drift.
2. Confirm candidate build and old/new static file hashes; ensure the candidate uses the current ACT test publishable key, other public variables preserved, and backend unchanged.
3. Start the candidate under a new named PM2 process on currently unused 127.0.0.1:3005 and verify non-public readiness without exposing credentials.
4. Preserve current port 3004 process, original static union and Nginx preimage. Prepare a reversible Nginx candidate changing only the three frontend upstreams and one static alias to the checked union. Validate candidate and rollback configs with nginx -t.
5. **Only after explicit owner production-switch approval**, atomically switch Nginx configuration, reload and verify public and origin pages/assets plus test payment form without pressing Book Now.
6. If verification fails, restore the exact Nginx preimage and reload after validation; leave both old and staged releases for inspection. Do not automatically change backend or any Stripe key.
7. After controlled payment test acceptance (one test attempt only with status verified), separately assess the **GBP 5.44 versus GBP 40 minimum fare** before broader booking-journey acceptance. The current quote/pricing source is not changed by this key repair.

A build or successful page load is NOT proof of confirmed payment, webhook fulfillment, pricing or full website acceptance.

## State as of recording

- Root cause: **confirmed on the active frontend** through owner-supplied read-only receipts.
- Replacement pk_test_ key: **validated** with same existing unpaid test intent; not installed.
- Development staging helper: **committed and locally tested only**.
- VPS staged frontend: **not built**.
- GitHub PR #115/#117: **open, draft, unmerged**.
- Production: current expired-key website still active; **no new deployment**.
