from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound, ParseError
from utils.common.locale_utils import get_locale
from utils.common.error_handlers import (
    create_validation_error_response,
    create_exception_error_response,
    create_not_found_response,
    create_unauthorized_response,
    create_forbidden_response,
    create_error_response,
    get_bilingual_error_message
)


class EMADBaseView(APIView):  
    permission_classes = [AllowAny]    
    
    def format_response(self, message, data=None, success=True, status_code=200, pagination=None):
        """
        Standardized response format:
        {
            "success": true/false,
            "message": "Message",
            "data": {...} or null,
            "pagination": {...} or null
        }
        """
        response = {
            "success": success,
            "message": message,
            "data": data,
            "pagination": pagination
        }
        return Response(response, status=status_code)
    
    def handle_request(self, request, method, *args, **kwargs):
        try:
            return method(request, *args, **kwargs)
        except ParseError as e:
            # Handle JSON parse errors (malformed JSON, extra data, etc.)
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                "Invalid JSON format in request body. Please check your request data.",
                "تنسيق JSON غير صحيح في نص الطلب. يرجى التحقق من بيانات الطلب.",
                locale
            )
            return create_error_response(
                message=message,
                errors=None,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        except PermissionDenied as e:
            locale = get_locale(request=request)
            return create_unauthorized_response(str(e), locale)
        
        except ValidationError as e:
            locale = get_locale(request=request)
            # Convert ValidationError detail to dict format if needed
            if isinstance(e.detail, dict):
                return create_validation_error_response(e.detail, locale)
            else:
                # If it's a list or string, convert to dict format
                errors = {'detail': e.detail} if not isinstance(e.detail, dict) else e.detail
                return create_validation_error_response(errors, locale)
        
        except NotFound as e:
            locale = get_locale(request=request)
            return create_not_found_response(str(e), locale)
        
        except Exception as e:
            locale = get_locale(request=request)
            return create_exception_error_response(e, locale)

    def get(self, request, *args, **kwargs):
        return self.handle_request(request, self.handle_get, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.handle_request(request, self.handle_post, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.handle_request(request, self.handle_put, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.handle_request(request, self.handle_patch, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        return self.handle_request(request, self.handle_delete, *args, **kwargs)

    def handle_get(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method.")

    def handle_post(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method.")

    def handle_put(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method.")

    def handle_patch(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method.")

    def handle_delete(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses should implement this method.")

    def get_messages(self, key, locale):
        """Fetches the appropriate error message based on the locale."""
        return self.MESSAGES.get(key, {}).get(locale, self.MESSAGES[key]["en"])




