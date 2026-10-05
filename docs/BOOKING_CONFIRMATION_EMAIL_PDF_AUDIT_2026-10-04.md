# Booking confirmation, email and PDF audit — 2026-10-04

**Status: draft reliability/security changes on PR #71. Not merged/deployed. No real customer email or Stripe charge was sent in this session.**

## Existing working foundation preserved

- Paid webhook-created Trip already stores passenger snapshot contact data, selected vehicle, price breakdown, route data, booking language and booking details.
- Booking PDF generation already exists and uses ACT logo assets; the repository contains `static/assets/act_logo.png`.
- The styled English booking email exists with booking/journey/passenger details, route link/map, Download Confirmation CTA, ACT imagery and support content.
- Arabic plus French/German/Spanish/Turkish/Simplified Chinese customer document paths already exist in the pending language work. Internal/owner notification is forced to English.
- The owner reports prior successful test trips reached email delivery without interruption. This remains historical evidence, not current-candidate regression evidence.

## Reliability finding: background thread could not prove delivery

The booking email helper previously started a daemon thread and returned success before Django/SMTP had actually accepted the message. A process restart or SMTP error after the return could therefore lose a confirmation while logs/callers believed it had been queued.

### Draft fix

Paid booking confirmation delivery now uses `apps.payments.tasks.deliver_paid_booking_confirmations`, discovered by the existing Celery app.

The task:
1. locks the paid Trip;
2. generates/persists the booking PDF if missing;
3. synchronously sends the passenger email and records `passenger_confirmation_sent_at` only after Django `send_mail` reports acceptance;
4. synchronously sends the English internal booking email and records `internal_booking_notification_sent_at` only after SMTP acceptance;
5. retries failures with exponential backoff.

A repeated Stripe success event safely requeues this task. Existing timestamps prevent normal retries from resending already-recorded passenger/internal messages. Exactly-once external SMTP delivery is not claimed: a process crash after SMTP accepts a message but before the DB timestamp commits can still cause a later duplicate. This is the standard at-least-once edge without provider-level idempotency.

Operational app/driver notifications remain separate from this paid-booking email task.

## PDF-link privacy finding

The English/localized email previously used the FileField media URL directly. The generated filename includes the numeric Trip ID, making the path predictable if media is publicly served.

### Draft fix

- Trip gets a unique random UUID `booking_confirmation_token`.
- Email Download Confirmation links use `/api/trips/booking-confirmation/<uuid>/` rather than the media filename.
- The download endpoint returns a PDF only for a paid Trip with that token and an existing confirmation file.
- Response is attachment-only with `Cache-Control: private, no-store` and `X-Content-Type-Options: nosniff`.
- No passenger/customer details are exposed by the token lookup response.

This is a bearer-link model: anyone possessing the emailed unguessable URL can download that confirmation. It avoids predictable public filenames but is not the same as account-authenticated access. Guest bookings require a bearer mechanism unless a separate guest verification flow is introduced.

## Vehicle rename + language consistency

Localized customer documents now resolve vehicle class translations by immutable VehicleType code first:
- comfort -> Comfort Class
- comfort_xl -> Comfort XL
- executive -> Executive Class
- executive_xl -> Executive XL
- first_class -> First Class

French/German/Spanish/Turkish/Simplified-Chinese document catalogues have matching professional class labels. Arabic reads the migrated `name_ar` value. Customer-entered names, addresses, airlines and notes remain verbatim. Internal owner email remains English.

## Asset/source checks

Confirmed repository assets include:
- ACT PDF logo: `static/assets/act_logo.png`;
- booking email header image;
- footer logo;
- manage-booking image;
- Google Play/App Store badges;
- social icons and charity CTA.

Repository presence does not prove those URLs are publicly reachable in the deployed environment. `APP_BASE_URL`, `ACT_EMAIL_ASSETS_BASE_URL`, static/media serving and SMTP settings must be checked on the isolated test environment.

## Tests added/updated (committed, not executed as full-suite evidence here)

- `apps/payments/test_booking_confirmations.py`: PDF + passenger/internal SMTP acceptance markers; retries skip already-recorded deliveries.
- `apps/trips/tests/test_booking_confirmation_download.py`: token URL is unguessable, paid PDF response uses private/no-store headers, unknown token returns 404.
- webhook reliability test updated so duplicate Stripe success requeues the idempotent confirmation task without repeating operational side effects.

## Acceptance scenarios still required

1. Run migration plan/check on isolated DB; verify existing Trips receive unique tokens.
2. Run backend suite with Celery eager/test configuration and frontend build.
3. Verify Celery worker discovers `apps.payments.tasks.deliver_paid_booking_confirmations`.
4. Use test SMTP/mailbox: one paid guest booking -> one passenger confirmation + one English ACT internal notification.
5. Repeat for signed-in passenger.
6. Replay the same Stripe success event; timestamps remain stable and normal retry does not send another recorded email.
7. Force passenger SMTP failure, then recover SMTP and verify task retry sends it and proceeds to internal notification.
8. Verify English + ar/fr/de/es/tr/zh-CN booking email/PDF values, direction, vehicle class, logo and links.
9. Click Download Confirmation from the received email: correct PDF downloads; raw predictable media URL is not the emailed link.
10. Verify APP_BASE_URL and email asset URLs are public HTTPS URLs in the test/release environment.
11. Confirm admin receives English regardless of customer booking language.
12. Confirm PDF/email facts match the persisted Trip and amount paid.

## Stripe test environment gate

Do not change production/live Stripe keys to perform acceptance. Stripe's current guidance uses sandboxes/test-mode API keys so test payments do not move real money. The sandbox/test webhook signing secret is separate from live. Configure an isolated ACT test environment with sandbox publishable key, sandbox secret key and sandbox webhook signing secret, then execute the payment/webhook scenarios against that environment.
