from twilio.rest import Client 
from django.conf import settings
from apps.trips.services.customer_language import normalize_language

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_verification_code(phone_number, locale=None):
    # Explicit website preference overrides phone-country inference. Other callers retain provider defaults.
    language = {"locale": normalize_language(locale)} if locale is not None else {}
    verification = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID) \
        .verifications \
        .create(to=phone_number, channel='sms', **language)
    return verification.status


def check_verification_code(phone_number, code):
    verification_check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID) \
        .verification_checks \
        .create(to=phone_number, code=code)
    return verification_check.status == 'approved'
