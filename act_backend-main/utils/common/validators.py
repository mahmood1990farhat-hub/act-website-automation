import phonenumbers
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _ 

def phone_number_is_valid(phone_number):
    """
    Validate phone number with bilingual error messages
    """
    try:
        # Check if phone number is provided
        if not phone_number:
            raise ValidationError({
                "error": [
                    _("Phone number is required."),
                    "رقم الهاتف مطلوب."
                ]
            })
        
        # Check if phone number starts with country code
        if not phone_number.startswith('+'):
            raise ValidationError({
                "error": [
                    _("Phone number must start with country code (e.g., +44 for UK, +1 for US)."),
                    "رقم الهاتف يجب أن يبدأ برمز الدولة (مثل: +44 للمملكة المتحدة، +1 للولايات المتحدة)."
                ]
            })
        
        # Check minimum length
        if len(phone_number) < 10:
            raise ValidationError({
                "error": [
                    _("Phone number is too short. Please use international format (e.g., +447700900123)."),
                    "رقم الهاتف قصير جداً. يرجى استخدام التنسيق الدولي (مثل: +447700900123)."
                ]
            })
        
        # Parse the phone number, assuming the phone number is in international format
        parsed_number = phonenumbers.parse(phone_number, None)  # 'None' defaults to the country code in the input
        
        # Check if the phone number is valid 
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValidationError({
                "error": [
                    _("Phone number is not valid. Please check the number and try again."),
                    "رقم الهاتف غير صحيح. يرجى التحقق من الرقم والمحاولة مرة أخرى."
                ]
            })
            
    except phonenumbers.phonenumberutil.NumberParseException:
        raise ValidationError({
            "error": [
                _("Invalid phone number format. Please use international format (e.g., +447700900123)."),
                "تنسيق رقم الهاتف غير صحيح. يرجى استخدام التنسيق الدولي (مثل: +447700900123)."
            ]
        })
    
    return phone_number

