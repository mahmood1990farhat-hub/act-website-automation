from twilio.rest import Client 
from django.conf import settings

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def send_verification_code(phone_number):
    verification = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID) \
        .verifications \
        .create(to=phone_number, channel='sms')
    return verification.status


def check_verification_code(phone_number, code):
    verification_check = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID) \
        .verification_checks \
        .create(to=phone_number, code=code)
    return verification_check.status == 'approved'
