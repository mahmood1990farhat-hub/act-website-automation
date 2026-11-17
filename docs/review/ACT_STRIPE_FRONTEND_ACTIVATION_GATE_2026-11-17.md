# ACT Stripe test publishable-key repair — controlled frontend release gate
Date: 17 November 2026. Website/backend workstream; GitHub PR #115, linked payment incident PR #117.

## Verified owner VPS evidence — keep separate from GitHub merge state

The existing ACT TEST backend secret can read the recorded unpaid PaymentIntent; the formerly active frontend `pk_test_` key returned HTTP 401 (`api_error / api_key_expired`). Nginx and running frontend CWD were checked against the expected 6 November release, and its compiled Stripe public key matched that expired key.

The owner entered a **replacement test publishable key** privately. Existing PaymentIntent GET confirmed **PASS: REPLACEMENT_TEST_PUBLIC_KEY_VALID; NO_CHANGES**.

After the owner gave permission for **inactive staging only**, the SHA-256-verified preparation helper ran on the VPS. The owner supplied:

```
Ran 12 tests ... OK
PASS: CURRENT_FRONTEND_SOURCE_AND_KEY_MATCH_RETAINED_RECEIPT
PASS: REPLACEMENT_KEY_READ_ONLY_VERIFIED
FRONTEND_CANDIDATE_PREPARED_NOT_ACTIVATED
CANDIDATE_RECORD: /root/act-release-backup/stripe-frontend-pk-20261117/plan.json
NO_PM2_NGINX_BACKEND_CHANGE
```

The owner then ran the SHA-256-verified, read-only post-build verifier on the VPS:

```
Ran 13 tests ... OK
PASS: INACTIVE_FRONTEND_CANDIDATE_VERIFIED
PASS: REPLACEMENT_TEST_KEY_IN_COMPILED_ASSETS
PASS: EIGHT_CRITICAL_APP_FILES_MATCH_PINNED_SOURCE
PASS: STATIC_ASSET_UNION_VERIFIED 149
PASS: CURRENT_FRONTEND_AND_BACKEND_PRESERVED
PASS: CANDIDATE_PORT_NOT_ACTIVE
NO_CHANGES; ACTIVATION_NOT_APPROVED
```

These are **owner-supplied host execution receipts**, not independent direct access to the VPS. Do not confuse with a live deployment, test card confirmation, a passing end-to-end booking, or proof that the new frontend is serving traffic.

## Pinned immutable release and rollback sources

- Existing accepted frontend application SHA: `02e59f95b5fd85d6ad07e881f3f2671a01a7bd65`. Retain its complete release at `/var/www/atg/front-end/releases/passenger-02e59f9-eoszulb3`, running on 127.0.0.1:3004.
- Existing accepted backend SHA: `d77e896af9daca5a39b7a85d5b76c5821e008d23`; no change permitted.
- Existing asset union: `/var/www/atg/front-end/act-static-passenger-02e59f9-eoszulb3`; preserve as rollback.
- New *inactive* frontend candidate: `/var/www/atg/front-end/releases/stripe-pk-02e59f9-20261117`, generated from **the exact same application SHA**, solely with the validated new test publishable key injected at build.
- New 149-file static union: `/var/www/atg/front-end/act-static-stripe-pk-02e59f9-20261117`.
- Private staging receipt: `/root/act-release-backup/stripe-frontend-pk-20261117/plan.json`.
- Source-only PR #115 includes `ops/payments/prepare_stripe_frontend_candidate.py`, `test_prepare_stripe_frontend_candidate.py` (12 tests), `verify_stripe_frontend_candidate.py`, `test_verify_stripe_frontend_candidate.py` (13 tests), plus the retained earlier release helper `ops/first-journey/passenger_frontend_release.py`. Reuse prior reviewed release mechanics; do not recreate the payment flow.

## Remaining deployment gate — explicit OWNER APPROVAL REQUIRED

A frontend-only release helper, drawing on the existing reviewed PM2/Nginx/rollback implementation, must be source-reviewed and tested before an activation command is offered. Its review should enforce the following **before any live mutation**:

1. Acquire the existing deployment lock; confirm current Nginx site resolution, unchanged backend process/source and shared environment, current 3004 frontend process, expected PM2 process inventory and saved dump, old build ID, new build ID, candidate `pk_test_` fingerprint and every static asset/hash.
2. Ensure new port 3005 is unused. Save private root-only Nginx, PM2 and relevant asset/source preimages and hashes; prepare proposed and rollback Nginx configs that alter **only exactly three** frontend `proxy_pass` endpoints (3004 -> 3005) and **one** static alias (old -> 149-file union). Validate both configs using `nginx -t` without changing live Nginx.
3. Start **one** candidate PM2 process on 127.0.0.1:3005 with the new build, without restarting, replacing or removing the 3004 process. Check direct loopback HTTP, correct build/assets and candidate identity before any public routing change.
4. Save the additional PM2 startup definition while preserving the previous saved state. Fail closed on process, file, Nginx or backend drift.
5. **Only with separate approval for the exact frontend-only production switch:** atomically install the reviewed Nginx candidate, reload Nginx once and check local-origin and public pages, build identity and statically served hashed assets. Require a bounded, documented success/rollback response.
6. On failure after any mutation, restore the exact preimage Nginx routing and original PM2 dump, and remove only the newly added candidate process if safe to do so. Keep all builds, assets and private logs. On an incomplete rollback, STOP and request manual review; do not assume success or blindly retry.
7. After deployment, verify that the checkout **form loads** without a card submission, source/passenger tracking still renders, and the backend remains unchanged. Record the actual deployed SHA/build receipt separately from PR merge state.

Do **not** modify backend `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, PaymentIntent code, Stripe webhook, booking/driver status, Google Maps, n8n, Android, cancellation terms or any other service to perform this repair.

## Critical separate fare gate

The prior unpaid test PaymentIntent is **GBP 5.44**, while the accepted ACT minimum fare is **GBP 40**. The reason for this difference is **not established** and must be investigated as a separate pricing acceptance item **before any new card confirmation**. A successful frontend switch only restores the potential to submit payment; it does NOT authorise a payment retry, real charge or full booking-to-completed-journey acceptance.

## State at this checkpoint

- Frontend build: **prepared on VPS, verified read-only by owner terminal; inactive**.
- Current production: **unchanged**; live frontend still carries expired key, so payment confirmation remains blocked.
- Frontend PR #115 and Stripe PR #117: **open, draft, unmerged**.
- New activation helper: **committed and locally safety-tested; VPS read-only validation and separate production approval remain required**.
- Production switch and further payment attempts: **not approved**.

## 17 November — live-switch preflight and owner-gated activation source

Owner VPS read-only result (the previously pinned script):
```
OK
PASS: PROPOSED_THREE_UPSTREAM_AND_ONE_ASSET_ALIAS_SWITCH
PASS: EXACT_NGINX_ROLLBACK_PREIMAGE
PASS: CURRENT_AND_SAVED_PM2_PROCESSES_PRESERVED
PASS: NEW_FRONTEND_PORT_UNUSED
PASS: STAGED_STRIPE_FRONTEND_STILL_VERIFIED
NO_CHANGES; NO_ACTIVATION_COMMAND
```

**Code now committed on the existing draft PR #115:**
- `ops/payments/activate_stripe_frontend.py` (source SHA-256 `6dee62263996e963d927b303311db5557fe563529be6ecccbfb86d0332923774`; Git blob `072dacf97c008c3904763f89380adbcd0173d8a4`)
- `ops/payments/test_activate_stripe_frontend.py` (source SHA-256 `f6cc13a33fb200bfa42355c176bd275e784cad70b5d20fbf005d9cadd820a3c7`; Git blob `04e90491151424a5d3043f9304b8ee536309c1f9`)

The source and test blobs match the locally verified bytes exactly. **22 new isolated local Python tests passed**. They cover the read-only CLI, test-mode/key handling boundary, approval/TTY/lock checks, immutable private release records, exact candidate-bound PM2 marker, Nginx/PM2 rollback/refusal on drift, bounded page checks, interruption/recovery outputs, and refusing any payment operation. No hosted CI or VPS execution of this new activation helper is claimed.

The helper `--check` is read-only. The separate `--activate` path has **NOT** been authorised, executed or runtime-tested on the VPS. It is gated by live preflight, root TTY, a separate exact approval phrase and existing release lock. It revalidates the candidate's test public key with provider **GETs** before switching, then uses the previously reviewed PM2 start/remove guards bound to the *new* root-private activation record. It preserves the running 3004 frontend; starts only the distinct 3005 candidate; saves the original PM2 and Nginx preimages; validates proposed+rollback Nginx configs; routes only the three frontend upstreams and one static alias; and attempts an automatic, candidate-only rollback if the activation fails. Recovery-incomplete is an explicit STOP, not a success.

**Remaining gate:** independently run only SHA-pinned new `--check` and the 22 affected offline tests on the VPS; review the result and explicit owner approval of the exact frontend-only production switch **before providing or executing any `--activate` command**. The GBP 5.44 versus GBP 40 discrepancy remains open; no new payment/card submission is approved. No backend/webhook/Android/automation changes, PR merge or production routing change occurred in this source preparation.
