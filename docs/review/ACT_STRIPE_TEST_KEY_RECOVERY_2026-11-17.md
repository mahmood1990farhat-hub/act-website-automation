# ACT Stripe test-key recovery — 17 November 2026

## Confirmed failure and approved scope

The owner could not advance from Confirm Booking Details to payment, including a fresh logged-out attempt. An independent guest website check reproduced HTTP 500 from `POST /api/trips/initiate-guest-payment/?locale=en` at 09:16:22 UTC on 17 November. A bounded submission through the existing Django browsable API exposed the server's reason: **Expired API Key provided**, classified as a Stripe test secret. Key values and suffixes are deliberately absent from this record.

The quote and guest details stages succeeded. The payment form never opened, and no payment was submitted. The connected ACT Stripe test account contained no new PaymentIntents in the scoped check. No server configuration, service, migration, webhook or application source was changed during diagnosis. Failed attempts can leave unpaid PendingPayment rows because the existing handler stores them before calling Stripe; no cleanup was performed.

The owner explicitly approved replacing the expired backend **test** secret and restarting `act.service`. This approval is limited to restoring the existing test checkout and checking that the guest payment form opens. It does not approve live payments, a code deployment, PR merge, migrations, changes to the webhook signing secret, Android packaging or dispatch activation.

## Existing configuration

- Recorded deployed backend: `d77e896af9daca5a39b7a85d5b76c5821e008d23`, PR #116, still open/draft/unmerged.
- Recorded deployed frontend: `02e59f95b5fd85d6ad07e881f3f2671a01a7bd65`; PR #115 documentation head `83691bf9974bd49eeeca41abb91bd67a2895c734`.
- Expected backend release: `/var/www/atg/atg-backend/releases/20261106-tracking-d77e896-oe9oh1vi/backend`.
- The release `.env` links to `/var/www/atg/atg-backend/shared/.env`.
- Django settings read `STRIPE_SECRET_KEY`; the payment modules cache it at import. The backend restart is therefore required after changing the approved setting.
- `STRIPE_WEBHOOK_SECRET` is a separate credential and is not part of this repair.
- Expected Stripe account: `acct_1RDnQjBxjYEaMc5N`, test mode. The public frontend was observed loading a test publishable key.

These are reviewed release records, not a substitute for the helper's fresh source and process checks on the host. An inherited Stripe environment override or unexpected release/configuration identity must stop the operation before writing.

## Owner terminal handoff

Run the recovery helper in the existing **Hostinger VPS root terminal**. The local preparation session does not have a direct server connection.

1. In the existing ACT Stripe account and test environment, obtain a current unexpired test secret. Keep it out of chat, screenshots, shell commands and source control.
2. Download the helper from its exact reviewed GitHub commit and verify its SHA-256 before running it. The final handoff supplies that pinned command.
3. Run `python3 <verified-helper-path> --apply`. The helper first checks the current service/configuration identity and then prompts for the new test secret with terminal echo disabled.
4. Share only the helper's fixed status output. A successful update/restart still requires the subsequent guest website payment-page check.

For a read-only source check, run the helper without `--apply` (or with `--check`). That does not prompt for or replace a key and does not restart a service.

The helper validates the candidate key with read-only Stripe requests before making a configuration change. It must reject a live key, the wrong account, an invalid/expired key, non-interactive key entry, source drift and ambiguous configuration. Only the single `STRIPE_SECRET_KEY` assignment may change. Existing file ownership/mode and all unrelated bytes must be preserved. The original environment file is retained in a root-private recovery directory and must never be uploaded or committed.

If the restart or readiness check fails after writing, retain the private backup and the fixed failure status for review. Do not run a second update or automatically restore the already-expired key. The helper must not send payment requests, restart Celery, run migrations, publish notifications or change Google/Stripe billing.

## Verification and status

The helper passed **20 focused Python unittest cases** using synthetic keys, temporary files and mocked subprocess/provider calls. The final added case verifies that even incorrect command-line key entry is never echoed by argparse. Independent source review and root review of the final redaction correction are complete. These results do not establish successful Hostinger execution or restored checkout. Unchanged application suites were not repeated.

Helper SHA-256: `3645e1062f6b69293815ab9f1730a2c9f0f6d5ce53be351ac331e378feafe36d`.

After owner execution reports a successful configuration update and backend readiness, make one fresh guest booking attempt through the passenger website and verify that the Stripe payment form opens in test mode. Stop before paying for this specific recovery check. The separate controlled booking-to-completed-journey acceptance remains open.

**Current status:** failure diagnosed; limited repair approved; recovery helper prepared and locally verified for the owner terminal handoff. The running server has not been changed and guest checkout is not yet confirmed restored. The source is retained on the separate `draft/act-stripe-test-key-recovery-20261117` branch based on the existing deployed backend; no application implementation is replaced.

## Sources

- [Current backend settings](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/d77e896af9daca5a39b7a85d5b76c5821e008d23/act_backend-main/myProject/settings/base.py).
- [Payment initiation](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/d77e896af9daca5a39b7a85d5b76c5821e008d23/act_backend-main/apps/trips/views/initiate_payment.py).
- [Existing staging helper](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/83691bf9974bd49eeeca41abb91bd67a2895c734/ops/first-journey/stage_existing_tracking.py).
- [Recorded activation checks](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/83691bf9974bd49eeeca41abb91bd67a2895c734/ops/first-journey/activate_existing_tracking.py).
- [Stripe key handling](https://docs.stripe.com/keys-best-practices).
