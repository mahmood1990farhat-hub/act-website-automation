from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from utils.common.locale_utils import get_locale
from utils.common.error_handlers import (
    get_bilingual_error_message,
    create_error_response
)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that formats all errors consistently
    Handles JWT authentication errors with bilingual messages
    """
    # Get locale from request
    request = context.get('request')
    locale = 'en'
    if request:
        locale = get_locale(request=request)
    
    # Handle JWT token errors
    if isinstance(exc, (InvalidToken, TokenError)):
        # Extract error message from exception
        error_detail = str(exc)
        
        # Check if exception has detail attribute with messages
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            # Extract message from messages array if available
            messages = exc.detail.get('messages', [])
            if messages and isinstance(messages, list) and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict) and 'message' in first_msg:
                    error_detail = first_msg['message']
        
        # Determine the error message based on the error type
        if 'expired' in error_detail.lower() or 'Token is expired' in error_detail:
            message = get_bilingual_error_message(
                'Your session has expired. Please log in again.',
                'انتهت صلاحية جلستك. يرجى تسجيل الدخول مرة أخرى.',
                locale
            )
            detail = get_bilingual_error_message(
                'Token is expired',
                'انتهت صلاحية الرمز المميز',
                locale
            )
        elif 'invalid' in error_detail.lower() or 'not valid' in error_detail.lower():
            message = get_bilingual_error_message(
                'Invalid authentication token. Please log in again.',
                'رمز المصادقة غير صحيح. يرجى تسجيل الدخول مرة أخرى.',
                locale
            )
            detail = get_bilingual_error_message(
                'Given token not valid for any token type',
                'الرمز المميز المقدم غير صالح لأي نوع من الرموز',
                locale
            )
        else:
            message = get_bilingual_error_message(
                'Authentication failed. Please log in again.',
                'فشلت المصادقة. يرجى تسجيل الدخول مرة أخرى.',
                locale
            )
            detail = get_bilingual_error_message(
                error_detail,
                error_detail,  # Will be replaced with Arabic if available
                locale
            )
        
        return create_error_response(
            message=message,
            detail=detail,
            locale=locale,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Handle AuthenticationFailed errors
    if isinstance(exc, AuthenticationFailed):
        message = get_bilingual_error_message(
            'Authentication failed. Please log in again.',
            'فشلت المصادقة. يرجى تسجيل الدخول مرة أخرى.',
            locale
        )
        detail = get_bilingual_error_message(
            str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            str(exc.detail) if hasattr(exc, 'detail') else str(exc),
            locale
        )
        
        return create_error_response(
            message=message,
            detail=detail,
            locale=locale,
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Call the default exception handler for other exceptions
    response = exception_handler(exc, context)
    
    if response is not None:
        # Format the response to match our standard format
        # Extract the error details
        error_data = response.data
        
        # Determine the error message
        if isinstance(error_data, dict):
            if 'detail' in error_data:
                detail_msg = str(error_data['detail'])
            elif 'message' in error_data:
                detail_msg = str(error_data['message'])
            else:
                # Get first error message
                detail_msg = str(list(error_data.values())[0][0]) if error_data else 'An error occurred'
        else:
            detail_msg = str(error_data)
        
        # Create standardized response
        return create_error_response(
            message=get_bilingual_error_message(
                'An error occurred',
                'حدث خطأ',
                locale
            ),
            detail=detail_msg,
            locale=locale,
            status_code=response.status_code
        )
    
    return response

