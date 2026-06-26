from django.utils.translation import gettext as _
from rest_framework.response import Response
from rest_framework import status


def get_bilingual_error_message(english_message, arabic_message, locale='en'):
    """
    Get error message based on locale
    """
    if locale == 'ar':
        return arabic_message
    return english_message


def format_validation_errors(errors, locale='en'):
    """
    Format validation errors with bilingual messages based on locale
    Returns field-specific errors (for backward compatibility)
    
    Handles different error formats:
    - dict: Field-based errors {field: [errors]}
    - str: Single error message
    - list: List of error messages
    """
    # Handle string errors
    if isinstance(errors, str):
        return {'non_field_errors': [errors]}
    
    # Handle list of errors
    if isinstance(errors, list):
        return {'non_field_errors': [str(error) for error in errors]}
    
    # Handle dict errors (expected format)
    if not isinstance(errors, dict):
        # If it's not a dict, convert to string and return as non_field_errors
        return {'non_field_errors': [str(errors)]}
    
    formatted_errors = {}
    
    for field, field_errors in errors.items():
        formatted_field_errors = []
        
        # Handle case where field_errors is a single string instead of a list
        if isinstance(field_errors, str):
            formatted_field_errors.append(field_errors)
        elif isinstance(field_errors, list):
            for error in field_errors:
                if isinstance(error, list) and len(error) == 2:
                    # Bilingual error message
                    english_msg = error[0]
                    arabic_msg = error[1]
                    message = get_bilingual_error_message(english_msg, arabic_msg, locale)
                    formatted_field_errors.append(message)
                else:
                    # Single language error message
                    formatted_field_errors.append(str(error))
        else:
            # Handle other types (e.g., ErrorDetail from DRF)
            formatted_field_errors.append(str(field_errors))
        
        formatted_errors[field] = formatted_field_errors
    
    return formatted_errors


def format_validation_errors_as_detail(errors, locale='en'):
    """
    Format validation errors as a single detail message
    Extracts the first error message and returns it as detail
    Handles different error formats: dict, string, list, ErrorDetail
    """
    from rest_framework.exceptions import ErrorDetail
    
    # Handle different error formats
    if isinstance(errors, str):
        # Already a string, return as is
        return errors
    
    if isinstance(errors, list):
        # List of errors, get first one
        if errors:
            error = errors[0]
            # Check if it's a list with bilingual messages
            if isinstance(error, list) and len(error) == 2:
                # Bilingual error message
                return get_bilingual_error_message(error[0], error[1], locale)
            # Check if it's ErrorDetail or list of ErrorDetails
            elif isinstance(error, ErrorDetail):
                error_str = str(error)
                # Try to find Arabic message in the list
                for e in errors:
                    if isinstance(e, ErrorDetail):
                        e_str = str(e)
                        # Check if this looks like Arabic (contains Arabic characters)
                        if any('\u0600' <= char <= '\u06FF' for char in e_str):
                            if locale == 'ar':
                                return e_str
                        elif locale == 'en':
                            return e_str
                return error_str
            return str(error)
        return 'Validation error'
    
    if not isinstance(errors, dict):
        # Convert to string if not dict
        return str(errors)
    
    # Flatten all errors into a list with field names
    all_errors = []
    
    for field, field_errors in errors.items():
        # Handle if field_errors is not a list
        if not isinstance(field_errors, list):
            field_errors = [field_errors]
        
        # Check if we have bilingual messages (list of ErrorDetails or list of lists)
        english_msg = None
        arabic_msg = None
        
        # First pass: check if it's a nested list [english, arabic]
        if len(field_errors) == 1 and isinstance(field_errors[0], list) and len(field_errors[0]) == 2:
            # Nested list format: [[english, arabic]]
            english_msg = str(field_errors[0][0])
            arabic_msg = str(field_errors[0][1])
        else:
            # Collect all messages and identify English vs Arabic
            all_messages = []
            for error in field_errors:
                if isinstance(error, list) and len(error) == 2:
                    # Bilingual error message as list [english, arabic]
                    english_msg = str(error[0])
                    arabic_msg = str(error[1])
                    break
                else:
                    # Convert to string
                    error_str = str(error)
                    all_messages.append(error_str)
            
            # If we didn't find a nested list, check the collected messages
            if not english_msg and not arabic_msg and all_messages:
                # Check each message for Arabic characters
                for msg in all_messages:
                    has_arabic = any('\u0600' <= char <= '\u06FF' for char in msg)
                    if has_arabic:
                        arabic_msg = msg
                    else:
                        english_msg = msg
                
                # If we have exactly 2 messages and found both, pair them
                if len(all_messages) == 2:
                    first = all_messages[0]
                    second = all_messages[1]
                    first_is_arabic = any('\u0600' <= char <= '\u06FF' for char in first)
                    second_is_arabic = any('\u0600' <= char <= '\u06FF' for char in second)
                    
                    if first_is_arabic and not second_is_arabic:
                        arabic_msg = first
                        english_msg = second
                    elif second_is_arabic and not first_is_arabic:
                        english_msg = first
                        arabic_msg = second
        
        # Format the error message with field name for better clarity
        field_display_name = format_field_name(field)
        
        # If we found both messages, use bilingual selection
        if english_msg and arabic_msg:
            # Always include field name for clarity
            english_msg = f"{field_display_name}: {english_msg}"
            arabic_msg = f"{field_display_name}: {arabic_msg}"
            message = get_bilingual_error_message(english_msg, arabic_msg, locale)
            all_errors.append(message)
        elif english_msg:
            # Always include field name for clarity
            english_msg = f"{field_display_name}: {english_msg}"
            all_errors.append(english_msg)
        elif arabic_msg:
            # Always include field name for clarity
            arabic_msg = f"{field_display_name}: {arabic_msg}"
            all_errors.append(arabic_msg)
        else:
            # Fallback to first error with field name
            error_text = str(field_errors[0]) if field_errors else 'Validation error'
            error_text = f"{field_display_name}: {error_text}"
            all_errors.append(error_text)
    
    # Return error message(s) as detail
    if all_errors:
        # If multiple errors, combine them for better clarity
        if len(all_errors) > 1:
            if locale == 'ar':
                return f"أخطاء في الحقول التالية: {'، '.join(all_errors)}"
            else:
                return f"Errors in the following fields: {'; '.join(all_errors)}"
        return all_errors[0]
    return 'Validation error'


def format_field_name(field_name):
    """
    Convert field name to a more readable format
    e.g., 'vehicle_ownership' -> 'Vehicle Ownership'
    """
    # Replace underscores with spaces and title case
    return field_name.replace('_', ' ').title()


def format_exception_error(exception, locale='en'):
    """
    Format exception errors with proper locale-based messages
    Logs the actual error for debugging while returning user-friendly messages
    """
    import logging
    import traceback
    
    logger = logging.getLogger(__name__)
    error_str = str(exception)
    error_type = type(exception).__name__
    
    # Log the actual error for debugging
    logger.error(f"Exception type: {error_type}, Message: {error_str}")
    logger.error(traceback.format_exc())
    
    # Handle ValidationError with bilingual messages
    if 'ErrorDetail' in error_str and 'string=' in error_str:
        # Extract the error details
        import re
        
        # Find all ErrorDetail strings
        error_details = re.findall(r"ErrorDetail\(string='([^']+)', code='[^']+'\)", error_str)
        
        if error_details:
            # Check if we have bilingual messages (English and Arabic)
            if len(error_details) == 2:
                english_msg = error_details[0]
                arabic_msg = error_details[1]
                return get_bilingual_error_message(english_msg, arabic_msg, locale)
            else:
                # Single message
                return error_details[0]
    
    # Handle specific error types with more descriptive messages
    error_lower = error_str.lower()
    
    # Stripe errors
    if 'stripe' in error_lower or error_type == 'StripeError':
        if locale == 'ar':
            return f'خطأ في معالجة الدفع: {error_str[:100]}'
        else:
            return f'Payment processing error: {error_str[:100]}'
    
    # Database errors
    if 'database' in error_lower or 'integrity' in error_lower or 'doesnotexist' in error_lower:
        if locale == 'ar':
            return 'خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى أو الاتصال بالدعم.'
        else:
            return 'Database error. Please try again or contact support.'
    
    # Network/API errors
    if 'connection' in error_lower or 'timeout' in error_lower or 'network' in error_lower:
        if locale == 'ar':
            return 'خطأ في الاتصال. يرجى التحقق من اتصالك بالإنترنت والمحاولة مرة أخرى.'
        else:
            return 'Connection error. Please check your internet connection and try again.'
    
    # Value/Type errors
    if error_type in ['ValueError', 'TypeError', 'AttributeError']:
        if locale == 'ar':
            return f'خطأ في البيانات: {error_str[:100]}'
        else:
            return f'Data error: {error_str[:100]}'
    
    # Handle other types of errors
    if locale == 'ar':
        if 'phone number is not valid' in error_lower:
            return 'رقم الهاتف غير صحيح. يرجى التحقق من الرقم والمحاولة مرة أخرى.'
        elif 'invalid phone number format' in error_lower:
            return 'تنسيق رقم الهاتف غير صحيح. يرجى استخدام التنسيق الدولي (مثل: +447700900123).'
        elif 'user with this email already exists' in error_lower:
            return 'عنوان البريد الإلكتروني مستخدم بالفعل. يرجى استخدام عنوان آخر.'
        elif 'user with this username already exists' in error_lower:
            return 'اسم المستخدم مستخدم بالفعل. يرجى استخدام اسم آخر.'
        elif 'no rate found' in error_lower or 'distance exceeds' in error_lower:
            return 'المسافة طويلة جداً أو نوع السيارة غير مدعوم. يرجى المحاولة بخيارات أخرى.'
        else:
            # Return the actual error message (truncated) for better debugging
            return f'حدث خطأ: {error_str[:150]}'
    else:
        if 'phone number is not valid' in error_lower:
            return 'Phone number is not valid. Please check the number and try again.'
        elif 'invalid phone number format' in error_lower:
            return 'Invalid phone number format. Please use international format (e.g., +447700900123).'
        elif 'user with this email already exists' in error_lower:
            return 'Email address already exists. Please use a different email.'
        elif 'user with this username already exists' in error_lower:
            return 'Username already exists. Please use a different username.'
        elif 'no rate found' in error_lower or 'distance exceeds' in error_lower:
            return 'Distance too long or car type not supported. Please try other options.'
        else:
            # Return the actual error message (truncated) for better debugging
            return f'Error: {error_str[:150]}'


def create_error_response(message, errors=None, locale='en', status_code=status.HTTP_400_BAD_REQUEST, detail=None):
    """
    Create a standardized error response with bilingual messages
    
    Standard format:
    {
        "success": false,
        "message": "Error message",
        "data": {
            "errors": {...}  // for validation errors
            "detail": "..."  // optional detail message
        },
        "pagination": null
    }
    
    Args:
        message: Main error message (string)
        errors: Validation errors (dict, list, or string) - optional
        locale: Locale for bilingual messages
        status_code: HTTP status code
        detail: Additional detail message (string) - optional
    """
    data = {}
    
    if errors:
        # format_validation_errors now handles dict, list, and string inputs
        formatted_errors = format_validation_errors(errors, locale)
        data['errors'] = formatted_errors
    
    if detail:
        # If detail is provided, add it as additional information
        if isinstance(detail, str):
            data['detail'] = detail
        else:
            data['detail'] = str(detail)
    
    response_data = {
        'success': False,
        'message': message,
        'data': data if data else None,
        'pagination': None
    }
    
    return Response(response_data, status=status_code)


def create_validation_error_response(serializer_errors, locale='en', custom_message=None):
    """
    Create standardized validation error response from serializer errors
    Returns errors as a single detail message instead of field-specific errors
    """
    if custom_message:
        message = custom_message
    else:
        message = get_bilingual_error_message(
            'Validation error',
            'خطأ في التحقق من البيانات',
            locale
        )
    
    # Format errors as a single detail message
    detail_message = format_validation_errors_as_detail(serializer_errors, locale)
    
    return create_error_response(
        message=message,
        detail=detail_message,
        locale=locale,
        status_code=status.HTTP_400_BAD_REQUEST
    )


def create_exception_error_response(exception, locale='en', custom_message=None):
    """
    Create standardized error response from exception
    """
    formatted_error = format_exception_error(exception, locale)
    
    if custom_message:
        message = custom_message
    else:
        message = get_bilingual_error_message(
            'An unexpected error occurred. Please try again.',
            'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.',
            locale
        )
    
    return create_error_response(
        message=message,
        detail=formatted_error,
        locale=locale,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def create_not_found_response(message, locale='en'):
    """
    Create standardized 404 not found response
    """
    return create_error_response(
        message=message,
        locale=locale,
        status_code=status.HTTP_404_NOT_FOUND
    )


def create_unauthorized_response(message=None, locale='en'):
    """
    Create standardized 401 unauthorized response
    """
    if not message:
        message = get_bilingual_error_message(
            'Authentication required. Please log in.',
            'المصادقة مطلوبة. يرجى تسجيل الدخول.',
            locale
        )
    
    return create_error_response(
        message=message,
        locale=locale,
        status_code=status.HTTP_401_UNAUTHORIZED
    )


def create_forbidden_response(message=None, locale='en'):
    """
    Create standardized 403 forbidden response
    """
    if not message:
        message = get_bilingual_error_message(
            'You do not have permission to perform this action.',
            'ليس لديك صلاحية لتنفيذ هذا الإجراء.',
            locale
        )
    
    return create_error_response(
        message=message,
        locale=locale,
        status_code=status.HTTP_403_FORBIDDEN
    )


def get_phone_number_examples():
    """
    Get phone number examples for different countries
    """
    return {
        'UK': '+447700900123',
        'US': '+15551234567',
        'France': '+33123456789',
        'Germany': '+49123456789',
        'UAE': '+971501234567',
        'Saudi Arabia': '+966501234567'
    }


def get_validation_messages(locale='en'):
    """
    Get validation messages based on locale
    """
    messages = {
        'en': {
            'required_field': 'This field is required.',
            'invalid_format': 'Invalid format.',
            'too_short': 'Value is too short.',
            'too_long': 'Value is too long.',
            'phone_required': 'Phone number is required.',
            'phone_invalid': 'Phone number is not valid.',
            'phone_format': 'Please use international format (e.g., +447700900123).',
            'email_invalid': 'Please enter a valid email address.',
            'password_short': 'Password must be at least 8 characters long.',
            'username_short': 'Username must be at least 3 characters long.',
            'username_long': 'Username must be no more than 10 characters long.',
            'name_short': 'Name must be at least 2 characters long.',
            'postcode_long': 'Postcode is too long (maximum 20 characters).',
            'list_required': 'Please provide a list of items.',
            'list_empty': 'List cannot be empty.',
        },
        'ar': {
            'required_field': 'هذا الحقل مطلوب.',
            'invalid_format': 'التنسيق غير صحيح.',
            'too_short': 'القيمة قصيرة جداً.',
            'too_long': 'القيمة طويلة جداً.',
            'phone_required': 'رقم الهاتف مطلوب.',
            'phone_invalid': 'رقم الهاتف غير صحيح.',
            'phone_format': 'يرجى استخدام التنسيق الدولي (مثل: +447700900123).',
            'email_invalid': 'يرجى إدخال عنوان بريد إلكتروني صحيح.',
            'password_short': 'كلمة المرور يجب أن تكون على الأقل 8 أحرف.',
            'username_short': 'اسم المستخدم يجب أن يكون على الأقل 3 أحرف.',
            'username_long': 'اسم المستخدم يجب ألا يزيد عن 10 أحرف.',
            'name_short': 'الاسم يجب أن يكون على الأقل حرفين.',
            'postcode_long': 'الرمز البريدي طويل جداً (الحد الأقصى 20 حرف).',
            'list_required': 'يرجى تقديم قائمة بالعناصر.',
            'list_empty': 'القائمة لا يمكن أن تكون فارغة.',
        }
    }
    
    return messages.get(locale, messages['en'])
