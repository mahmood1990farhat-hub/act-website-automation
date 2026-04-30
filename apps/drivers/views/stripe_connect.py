"""
Stripe Connect for drivers: Connected Accounts (Express).

Passengers pay the platform via Stripe; the platform can then transfer earnings
to drivers who have completed Stripe Connect onboarding. Stripe holds KYC and
bank details for connected drivers – we do not store their bank account for
Connect payouts.
"""
from rest_framework.response import Response
from rest_framework import status
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsVerifiedAndProfileCompleted, IsNormalDriver
from utils.common import get_locale
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateStripeConnectAccountView(EMADBaseView):
    """
    Create a Stripe Connect Express account for the driver and return an
    onboarding URL. Frontend should redirect the driver to this URL so they
    can complete KYC and add their bank account in Stripe (we do not store
    bank details for Connect payouts).

    POST /api/drivers/stripe-connect/create/ or POST /api/drivers/stripe/connect/
    Optional body: { "return_url": "https://app.example.com/payout/return",
                     "refresh_url": "https://app.example.com/payout/refresh" }
    """
    permission_classes = [IsVerifiedAndProfileCompleted, IsNormalDriver]
    http_method_names = ['post']

    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)

        driver = request.user.base_driver
        if not driver:
            message = get_bilingual_error_message(
                'Driver profile not found',
                'ملف السائق غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        # Already onboarded: do not create a second Connect account
        if driver.stripe_account_id:
            message = get_bilingual_error_message(
                'Stripe account already exists',
                'حساب Stripe موجود بالفعل',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            # --- Step 1: Create Stripe Connect Express account ---
            # Express accounts are managed by the platform; Stripe hosts onboarding.
            # Idempotency key ensures we do not create duplicate accounts on retries.
            idempotency_key = f"connect_account_driver_{driver.id}"
            account = stripe.Account.create(
                type="express",
                country="GB",
                email=request.user.email,
                capabilities={
                    "transfers": {"requested": True},  # Required to receive Transfers from platform
                },
                idempotency_key=idempotency_key
            )

            # Persist Connect account id so we can use it for stripe.Transfer.create in payouts
            driver.stripe_account_id = account.id
            driver.save(update_fields=['stripe_account_id'])

            # --- Step 2: Create AccountLink for onboarding ---
            # Driver must complete this flow in the browser (KYC + bank details in Stripe).
            # We do NOT store bank numbers when using Connect; Stripe holds them.
            data = getattr(request, 'data', None) or {}
            return_url = data.get('return_url') or request.build_absolute_uri('/api/drivers/stripe-connect/return')
            refresh_url = data.get('refresh_url') or request.build_absolute_uri('/api/drivers/stripe-connect/refresh')
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url=refresh_url,  # Where to send driver if link expires
                return_url=return_url,   # Where to send driver after onboarding completes
                type="account_onboarding"
            )

            logger.info(f"Stripe Connect account created for driver {driver.id}: {account.id}")

            return Response({
                "success": True,
                "data": {
                    "account_id": account.id,
                    "onboarding_url": account_link.url,  # Frontend redirects driver here
                }
            }, status=status.HTTP_200_OK)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating Connect account: {str(e)}")
            message = get_bilingual_error_message(
                'Error creating Stripe account. Please try again.',
                'خطأ في إنشاء حساب Stripe. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error creating Stripe Connect account: {str(e)}")
            message = get_bilingual_error_message(
                'An error occurred. Please try again.',
                'حدث خطأ. يرجى المحاولة مرة أخرى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

