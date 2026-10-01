# Step 1 onboarding logging fix

Prepared 1 October 2026 against backend repository commit `5c66b4547cab23b3fb166caab70f830e1ac38d6e`.

## Change

Removed direct debug prints from `DriverOnboardingStep1View.handle_post`, including submitted `confirm_password`, serializer fields/errors, validated-data keys and raw save exceptions. Removed direct traceback printing. Unexpected save failures now emit one fixed event message, without exception arguments or traceback, and return a generic localized 500 response through `create_error_response`.

The previous generic exception helper logs exception text/traceback and can return raw exception details. This handler no longer calls it. The shared helper itself is unchanged to avoid altering unrelated endpoints. Successful creation, confirmation-email calls, validation-error responses and duplicate-account handling are retained. All other classes in the file and its module imports are unchanged.

## Verification

Run from `act_backend-main`:

`python -m unittest discover -s tests -p 'test_onboarding_logging.py' -v`

Eleven tests passed. They extract the actual handler AST and run it with synthetic serializer, email, response and logger stubs. Synthetic sensitive sentinels do not reach stdout, stderr or logger calls. Tests cover success, serializer rejection, save validation errors, unexpected errors, Arabic response, duplicate email/phone and wrapped integrity errors. A structural regression rejects direct print/traceback calls and nonconstant logger arguments in the handler.

These tests do not execute Django/DRF middleware, real serializers, database transactions, email services or the web server. Validation errors still follow the existing response contract; this is not a claim that all response bodies or every application log are sanitized. No real credentials, request records or production logs were accessed.

## Deployment and follow-up

This source fix is not proof of a deployed fix. No deployment was invoked. Review the exact commit in staging and verify signup success, validation failures and duplicate-account responses with synthetic data before the separate production deployment. The inspected backend Actions workflow is manually dispatched with an exact commit SHA.

Historical exposure remains unknown. Removing source logging does not remove old logs or establish whether this revision was running in production. If deployed exposure is confirmed, review retention/access and the need for credential remediation through an authorized operational process. Do not export password-containing logs, and do not delete evidence or rotate user credentials automatically.
