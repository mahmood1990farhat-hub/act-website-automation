from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _, activate
from django.db import IntegrityError
from django.db.utils import DatabaseError
from utils.common import get_locale, remove_empty_values, paginate_queryset
from utils.common.error_handlers import get_bilingual_error_message
from ..serializers import (
    DriverOnboardingQuestionnaireSerializer,
    DriverOnboardingRequestSerializer,
    DriverOnboardingApprovalSerializer
)
from ..models import DriverOnboardingRequest
from django.contrib.auth import get_user_model
from django.db.models import Q
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class DriverOnboardingStep1View(EMADBaseView):
    """
    Step 1: Driver submits questionnaire and basic information
    Creates a pending onboarding request for admin review
    """
    http_method_names = ['post']
    
    def handle_post(self, request):
        activate(get_locale(request=request))
        
        # Debug: Check the data
        data = request.data
        print("=" * 80)
        print("DEBUG: Raw request data:")
        print(f"  - confirm_password present: {'confirm_password' in data}")
        print(f"  - confirm_password value: {data.get('confirm_password')}")
        print(f"  - All keys: {list(data.keys())}")
        
        serializer = DriverOnboardingQuestionnaireSerializer(data=data)
        print(f"DEBUG: Serializer fields: {list(serializer.fields.keys())}")
        print(f"DEBUG: confirm_password field: {serializer.fields.get('confirm_password')}")
        print(f"DEBUG: confirm_password required: {serializer.fields.get('confirm_password').required if 'confirm_password' in serializer.fields else 'N/A'}")
        
        is_valid = serializer.is_valid()
        print(f"DEBUG: Serializer is_valid: {is_valid}")
        if not is_valid:
            print(f"DEBUG: Serializer errors: {serializer.errors}")
            print("=" * 80)
            
            # Get locale from request
            locale = get_locale(request=request)
            
            # Use standardized validation error response with custom message
            from utils.common.error_handlers import create_validation_error_response
            custom_message = get_bilingual_error_message(
                'Error creating onboarding request',
                'خطأ في إنشاء طلب التسجيل',
                locale
            )
            return create_validation_error_response(serializer.errors, locale, custom_message)
        
        print(f"DEBUG: Validated data keys: {list(serializer.validated_data.keys())}")
        
        try:
            onboarding_request = serializer.save()
            print(f"DEBUG: Successfully saved onboarding request: {onboarding_request.id}")
            print("=" * 80)
        except ValidationError as e:
            # Validation errors should return 400, not 500
            print(f"DEBUG: Validation error during save: {type(e).__name__}: {str(e)}")
            print("=" * 80)
            
            # Get locale from request
            locale = get_locale(request=request)
            
            # Use standardized validation error response
            from utils.common.error_handlers import create_validation_error_response
            custom_message = get_bilingual_error_message(
                'Error creating onboarding request',
                'خطأ في إنشاء طلب التسجيل',
                locale
            )
            # Convert ValidationError detail to proper format
            # format_validation_errors_as_detail handles dict, string, and list formats
            if isinstance(e.detail, dict):
                errors = e.detail
            elif isinstance(e.detail, list):
                # If it's a list, convert to dict with 'detail' key
                errors = {'detail': e.detail}
            else:
                # If it's a string, convert to dict with 'detail' key
                errors = {'detail': [str(e.detail)]}
            return create_validation_error_response(errors, locale, custom_message)
        except Exception as e:
            print(f"DEBUG: Error during save: {type(e).__name__}: {str(e)}")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            
            # Get locale from request
            locale = get_locale(request=request)
            
            # Check if it's a database integrity error (duplicate key)
            # Django wraps IntegrityError in DatabaseError, so check both
            integrity_error = None
            if isinstance(e, IntegrityError):
                integrity_error = e
            elif isinstance(e, DatabaseError) and hasattr(e, '__cause__'):
                if isinstance(e.__cause__, IntegrityError):
                    integrity_error = e.__cause__
            elif hasattr(e, '__cause__') and isinstance(e.__cause__, IntegrityError):
                integrity_error = e.__cause__
            
            if integrity_error:
                # Use the extracted IntegrityError
                error_message = str(integrity_error)
                
                # Check if it's a duplicate email error
                if 'email' in error_message.lower() and 'unique' in error_message.lower():
                    message = get_bilingual_error_message(
                        'An account with this email address already exists. Please use a different email or try logging in.',
                        'حساب بهذا البريد الإلكتروني موجود بالفعل. يرجى استخدام بريد إلكتروني آخر أو محاولة تسجيل الدخول.',
                        locale
                    )
                    from utils.common.error_handlers import create_error_response
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check if it's a duplicate phone number error
                elif 'phone' in error_message.lower() and 'unique' in error_message.lower():
                    message = get_bilingual_error_message(
                        'An account with this phone number already exists. Please use a different phone number.',
                        'حساب بهذا رقم الهاتف موجود بالفعل. يرجى استخدام رقم هاتف آخر.',
                        locale
                    )
                    from utils.common.error_handlers import create_error_response
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
                
                # Generic integrity error
                else:
                    message = get_bilingual_error_message(
                        'This information is already registered. Please check your email and phone number.',
                        'هذه المعلومات مسجلة بالفعل. يرجى التحقق من بريدك الإلكتروني ورقم هاتفك.',
                        locale
                    )
                    from utils.common.error_handlers import create_error_response
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            # Use standardized exception error response for other errors
            from utils.common.error_handlers import create_exception_error_response
            custom_message = get_bilingual_error_message(
                'Error creating onboarding request',
                'خطأ في إنشاء طلب التسجيل',
                locale
            )
            return create_exception_error_response(e, locale, custom_message)
        
        # Send confirmation emails
        from utils.common.email import send_driver_onboarding_submitted, send_admin_onboarding_notification
        send_driver_onboarding_submitted(onboarding_request)
        send_admin_onboarding_notification(onboarding_request)
        
        return Response({
            'message': _('Your onboarding request has been submitted successfully. We will review your application and get back to you soon.'),
            'onboarding_request_id': onboarding_request.id,
            'status': 'pending'
        }, status=status.HTTP_201_CREATED)

class DriverOnboardingStep2View(EMADBaseView):
    """
    Step 2: Driver uploads documents after admin approval
    This replaces the old CompleteNormalDriverInfoView
    """
    http_method_names = ['post']
    permission_classes = [IsAuthenticated]
    
    def handle_post(self, request):
        activate(get_locale(request=request))
        user = request.user
        
        # Check if user has an approved onboarding request
        try:
            onboarding_request = user.driver_onboarding_request
            if onboarding_request.status != 'approved':
                return Response({
                    'error': _('Your onboarding request must be approved before you can upload documents.')
                }, status=status.HTTP_400_BAD_REQUEST)
        except DriverOnboardingRequest.DoesNotExist:
            return Response({
                'error': _('No onboarding request found. Please complete step 1 first.')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already has a driver account
        if hasattr(user, 'base_driver'):
            raise ValidationError({"detail": "This user already has a driver account."})
        
        # Process document uploads (reuse existing logic from CompleteNormalDriverInfoView)
        nested_data = self.prepare_data(request.data)
        
        # If vehicle_type is not provided in request, try to get it from onboarding request
        if 'vehicle_data' in nested_data and not nested_data['vehicle_data'].get('vehicle_type'):
            try:
                onboarding_request = user.driver_onboarding_request
                if onboarding_request.vehicle_type:
                    nested_data['vehicle_data']['vehicle_type'] = onboarding_request.vehicle_type
            except Exception:
                pass  # If onboarding request doesn't exist, continue without vehicle_type
        
        from ..serializers import RegisterFullNormalDriverSerializer
        serializer = RegisterFullNormalDriverSerializer(data=nested_data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        normal_driver = serializer.save()
        
        return Response({
            'message': _('Your driver account has been created successfully!'),
            'normal_driver_id': normal_driver.id
        }, status=status.HTTP_201_CREATED)
    
    def prepare_data(self, data):
        """Prepare data for document upload (reuse existing logic)"""
        nested_data = {
            "pco": data.get("pco"),
            "dbs": data.get("dbs"),
            "dvla": data.get("dvla"),
            "bank_details_data": {
                "bank_account_number": data.get("bank_account_number"),
                "sort_code": data.get("sort_code"),
                "registered_address": data.get("registered_address"),
            },
            "vehicle_data": {
                "vehicle_number": data.get("vehicle_number"),
                "year_of_manufacture": data.get("year_of_manufacture"),
                "mot": data.get("mot"),
                "phv": data.get("phv"),
                "vehicle_type": data.get("vehicle_type"),
            },
            "interview_data": {
                "interview_date": data.get("interview_date"),
                "interview_time": data.get("interview_time"),
            }
        }
        return remove_empty_values(nested_data)

class AdminOnboardingRequestsListView(EMADBaseView):
    """
    Admin view to list and filter onboarding requests
    """
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request):
        activate(get_locale(request=request))
        
        # Get filter parameters
        status_filter = request.GET.get('status')
        search = request.GET.get('search')
        ordering = request.GET.get('ordering', '-created_at')
        
        # Build queryset
        queryset = DriverOnboardingRequest.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(email_address__icontains=search) |
                Q(mobile_number__icontains=search)
            )
        
        queryset = queryset.order_by(ordering)
        
        # Paginate the queryset
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = DriverOnboardingRequestSerializer(page_obj, many=True)
        
        return Response({
            'data': serializer.data,
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'page_size': paginator.per_page,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
            'total_count': DriverOnboardingRequest.objects.count(),
            'pending_count': DriverOnboardingRequest.objects.filter(status='pending').count(),
            'step1_approved_count': DriverOnboardingRequest.objects.filter(status='step1_approved').count(),
            'documents_uploaded_count': DriverOnboardingRequest.objects.filter(status='documents_uploaded').count(),
            'final_approved_count': DriverOnboardingRequest.objects.filter(status='final_approved').count(),
            'final_rejected_count': DriverOnboardingRequest.objects.filter(status='final_rejected').count(),
            'step1_rejected_count': DriverOnboardingRequest.objects.filter(status='step1_rejected').count(),
            'needs_modification_count': DriverOnboardingRequest.objects.filter(status='needs_modification').count(),
        })

class AdminOnboardingRequestDetailView(EMADBaseView):
    """
    Admin view to get details of a specific onboarding request including uploaded documents
    """
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request, request_id):
        activate(get_locale(request=request))
        
        try:
            onboarding_request = DriverOnboardingRequest.objects.get(id=request_id)
        except DriverOnboardingRequest.DoesNotExist:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'Onboarding request not found.',
                'لم يتم العثور على طلب التسجيل.',
                locale
            )
            from utils.common.error_handlers import create_not_found_response
            return create_not_found_response(message, locale)
        
        serializer = DriverOnboardingRequestSerializer(onboarding_request)
        response_data = serializer.data
        
        # Add modification status information
        response_data['files_need_modification'] = onboarding_request.files_need_modification or []
        response_data['modification_confirmed'] = onboarding_request.modification_confirmed
        
        # Map file names to user-friendly labels
        if onboarding_request.files_need_modification:
            file_labels = {
                'pco': 'PCO License',
                'dbs': 'DBS Certificate',
                'dvla': 'DVLA License',
                'mot': 'MOT Certificate',
                'phv': 'PHV License'
            }
            response_data['files_need_modification_labels'] = [
                file_labels.get(f, f.upper()) for f in onboarding_request.files_need_modification
            ]
        
        # Add uploaded documents if available (for step 2 and beyond)
        if onboarding_request.status in ['documents_uploaded', 'needs_modification', 'final_approved', 'final_rejected']:
            documents_data = self.get_driver_documents(onboarding_request.user)
            if documents_data:
                response_data['documents'] = documents_data
        
        return Response(response_data)
    
    def file_to_base64(self, file_field):
        """Convert file field to base64 string with metadata"""
        if not file_field:
            return None
        
        try:
            import base64
            import os
            
            file_field.open()
            file_content = file_field.read()
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            file_field.close()
            
            # Get file metadata
            filename = os.path.basename(file_field.name) if file_field.name else None
            file_extension = os.path.splitext(filename)[1] if filename else None
            
            return {
                'content': file_base64,
                'filename': filename,
                'extension': file_extension,
                'size': len(file_content)
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error converting file to base64: {str(e)}")
            return None
    
    def get_driver_documents(self, user):
        """Get driver's uploaded documents as base64"""
        try:
            base_driver = user.base_driver
            documents = {
                'pco': self.file_to_base64(base_driver.pco) if base_driver.pco else None,
                'dbs': self.file_to_base64(base_driver.dbs) if base_driver.dbs else None,
                'dvla': self.file_to_base64(base_driver.dvla) if base_driver.dvla else None,
            }
            
            # Get bank details if available
            if base_driver.bank_details:
                bank = base_driver.bank_details
                documents['bank_details'] = {
                    'bank_account_number': str(bank.bank_account_number) if bank.bank_account_number else None,
                    'sort_code': str(bank.sort_code) if bank.sort_code else None,
                    'registered_address': str(bank.registered_address) if bank.registered_address else None,
                }
            
            # Get vehicle details if available
            try:
                normal_driver = base_driver.normal_driver
                if normal_driver.vehicle:
                    vehicle = normal_driver.vehicle
                    vehicle_data = {
                        'vehicle_number': str(vehicle.vehicle_number) if vehicle.vehicle_number else None,
                        'year_of_manufacture': int(vehicle.year_of_manufacture) if vehicle.year_of_manufacture else None,
                        'mot': self.file_to_base64(vehicle.mot) if vehicle.mot else None,
                        'phv': self.file_to_base64(vehicle.phv) if vehicle.phv else None,
                    }
                    
                    # Handle vehicle_type (ForeignKey to VehicleType model)
                    if vehicle.vehicle_type:
                        vehicle_data['vehicle_type'] = {
                            'id': vehicle.vehicle_type.id,
                            'name_en': str(vehicle.vehicle_type.name_en),
                            'name_ar': str(vehicle.vehicle_type.name_ar),
                        }
                    else:
                        vehicle_data['vehicle_type'] = None
                    
                    documents['vehicle'] = vehicle_data
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting vehicle details: {str(e)}")
            
            # Get interview details if available
            try:
                interview = user.interview
                documents['interview'] = {
                    'interview_date': interview.interview_date.isoformat() if interview.interview_date else None,
                    'interview_time': interview.interview_time.isoformat() if interview.interview_time else None,
                }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting interview details: {str(e)}")
            
            return documents
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting driver documents: {str(e)}")
            return None

class AdminOnboardingRequestActionView(EMADBaseView):
    """
    Admin view to approve or reject onboarding requests
    """
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, request_id):
        activate(get_locale(request=request))
        
        try:
            onboarding_request = DriverOnboardingRequest.objects.get(id=request_id)
        except DriverOnboardingRequest.DoesNotExist:
            return Response({
                'error': _('Onboarding request not found.')
            }, status=status.HTTP_404_NOT_FOUND)
        
        if onboarding_request.status != 'pending':
            return Response({
                'error': _('This request has already been processed.')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = DriverOnboardingApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        
        try:
            if action == 'approve':
                onboarding_request.approve_step1(request.user, notes)
                
                # Send step 1 approval email (won't fail if email sending fails)
                from utils.common.email import send_driver_step1_approval
                send_driver_step1_approval(onboarding_request)
                
                # Send push notification to driver
                try:
                    from utils.common import notify_user
                    locale = get_locale(request=request)
                    notify_user(
                        user=onboarding_request.user.id,
                        title_en='Step 1 Approved!',
                        title_ar='تمت الموافقة على الخطوة 1!',
                        desc_en='Your initial application has been approved. You can now upload your documents.',
                        desc_ar='تمت الموافقة على طلبك الأولي. يمكنك الآن تحميل المستندات الخاصة بك.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for step1_approved: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': _('Step 1 approved. User can now upload documents.'),
                    'status': 'step1_approved'
                })
            
            elif action == 'reject':
                if not rejection_reason:
                    locale = get_locale(request=request)
                    message = get_bilingual_error_message(
                        'Rejection reason is required.',
                        'سبب الرفض مطلوب.',
                        locale
                    )
                    from utils.common.error_handlers import create_error_response
                    return create_error_response(message, locale=locale)
                
                onboarding_request.reject_step1(request.user, rejection_reason)
                
                # Send step 1 rejection email (won't fail if email sending fails)
                from utils.common.email import send_driver_step1_rejection
                send_driver_step1_rejection(onboarding_request, rejection_reason)
                
                # Send push notification to driver
                try:
                    from utils.common import notify_user
                    locale = get_locale(request=request)
                    notify_user(
                        user=onboarding_request.user.id,
                        title_en='Application Update',
                        title_ar='تحديث الطلب',
                        desc_en='Your initial application was not approved at this time. Please check your email for details.',
                        desc_ar='لم تتم الموافقة على طلبك الأولي في هذا الوقت. يرجى التحقق من بريدك الإلكتروني للتفاصيل.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for step1_rejected: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': _('Step 1 rejected.'),
                    'status': 'step1_rejected'
                })
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Error processing onboarding request {request_id}: {str(e)}", exc_info=True)
            
            # Get locale for error message
            locale = get_locale(request=request)
            
            custom_message = get_bilingual_error_message(
                'An error occurred while processing the request. Please try again.',
                'حدث خطأ أثناء معالجة الطلب. يرجى المحاولة مرة أخرى.',
                locale
            )
            
            from utils.common.error_handlers import create_exception_error_response
            return create_exception_error_response(e, locale, custom_message)
    
