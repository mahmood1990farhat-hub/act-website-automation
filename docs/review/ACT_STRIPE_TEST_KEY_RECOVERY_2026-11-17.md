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

## Read-only host result and metadata review

The owner ran the original pinned helper with `--check`. It stopped with `ENV_EXTENDED_ATTRIBUTES_REQUIRE_REVIEW; STAGE=UNCHANGED`, exit 1. The owner confirmed that the environment file was unchanged and `act.service` was not restarted. The terminal screenshot lists one attribute, `user.security.m.metadata`, with 79 bytes. Its value was not printed or retained in this record.

Monarx documents this exact attribute name as metadata normally managed by its malware scanner. Hostinger documents using Monarx for its VPS malware scanner. This is consistent with expected scanner operation, but the name alone does not prove which process last wrote the specific value on this host. The Monarx article also states that other tools can set or copy attributes in the `user.` namespace. No direct host audit or scanner-presence check has been performed by this session.

The revised helper supports only this reviewed attribute. It snapshots the opaque bytes, includes them and the change timestamp in drift checks, copies and verifies them on the private backup and temporary replacement, and checks the installed result. All other file attributes and default directory ACLs still require review. No attributes are deleted, no scanner is disabled or reconfigured, and metadata values never appear in status output.

The deployment lock does not coordinate with the malware scanner. If its metadata changes during recovery, the helper can stop conservatively. A post-write stop retains the new configuration and private backup for review; it does not silently restore the expired key or retry the service restart. Such a stop is not evidence of compromise.

## Verification and status

The revised helper passed **28 focused Python unittest cases** in one run: the 20 existing recovery checks plus 8 focused metadata cases. Real temporary filesystem attributes verified preservation of a synthetic 79-byte value. Other cases cover unreadable attributes, same-length drift, removal, changes during reads, failed copies, read-back mismatch, unknown/ACL attributes and post-write drift. Stripe and systemd calls were mocked. An independent read-only source review of the exact revised helper found no material blocker. These results do not establish successful Hostinger application or restored checkout. Unchanged website/Android suites were not repeated.

Helper SHA-256: `6b412d93c7bd563901c9fe0b031c718b76671ba4e906e5144b00e6dc546b99fe`.

Test source SHA-256: `4c48675285e4c2d5b062c9c574a52c68dbceb88ff21d8fd2134b364dab0cc6bf`.

After owner execution reports a successful configuration update and backend readiness, make one fresh guest booking attempt through the passenger website and verify that the Stripe payment form opens in test mode. Stop before paying for this specific recovery check. The separate controlled booking-to-completed-journey acceptance remains open.

**Current status:** failure diagnosed; limited repair approved; original read-only host check stopped safely; metadata-preserving revision tested and independently reviewed, awaiting owner execution. The server key has not been replaced, the service has not been restarted, and guest checkout is not yet confirmed restored. Work remains in draft PR #117 on `draft/act-stripe-test-key-recovery-20261117`, based on the existing deployed backend.

## Sources

- [Current backend settings](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/d77e896af9daca5a39b7a85d5b76c5821e008d23/act_backend-main/myProject/settings/base.py).
- [Payment initiation](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/d77e896af9daca5a39b7a85d5b76c5821e008d23/act_backend-main/apps/trips/views/initiate_payment.py).
- [Existing staging helper](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/83691bf9974bd49eeeca41abb91bd67a2895c734/ops/first-journey/stage_existing_tracking.py).
- [Recorded activation checks](https://github.com/mahmood1990farhat-hub/act-website-automation/blob/83691bf9974bd49eeeca41abb91bd67a2895c734/ops/first-journey/activate_existing_tracking.py).
- [Stripe key handling](https://docs.stripe.com/keys-best-practices).
- [Monarx attribute documentation](https://support.monarx.com/en/articles/17640278-what-is-the-user-security-m-metadata-extended-attribute).
- [Hostinger VPS malware scanner](https://www.hostinger.com/support/8450363-hostinger-vps-malware-scanner/).
