from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils.translation import gettext as _
from django.utils.translation import activate
import logging

from utils.EMDBase import EMADBaseView
from utils.common.locale_utils import get_locale
from utils.common.cleaners import remove_empty_values
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    create_exception_error_response,
    get_bilingual_error_message
)
from ..models import DriverOnboardingRequest

logger = logging.getLogger(__name__)


class DriverOnboardingStep2View(EMADBaseView):
    """
    Step 2: Driver uploads documents after Step 1 approval
    """
    http_method_names = ['post']
    permission_classes = [IsAuthenticated]
    
    def handle_post(self, request):
        activate(get_locale(request=request))
        user = request.user
        
        # Check if user has an approved step 1 onboarding request or needs modification
        try:
            onboarding_request = user.driver_onboarding_request
            if onboarding_request.status not in ['step1_approved', 'needs_modification']:
                locale = get_locale(request=request)
                message = get_bilingual_error_message(
                    'Your step 1 must be approved before you can upload documents.',
                    'يجب الموافقة على الخطوة الأولى قبل رفع المستندات.',
                    locale
                )
                return create_error_response(message, locale=locale)
        except DriverOnboardingRequest.DoesNotExist:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'No onboarding request found. Please complete step 1 first.',
                'لم يتم العثور على طلب التسجيل. يرجى إكمال الخطوة الأولى أولاً.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # Handle modification case - partial file uploads
        if onboarding_request.status == 'needs_modification':
            return self._handle_modification_upload(request, onboarding_request, user)
        
        # Normal flow - initial document upload
        # Process document uploads (reuse existing logic from CompleteNormalDriverInfoView)
        # prepare_data will automatically get vehicle_type from onboarding_request if not in request
        nested_data = self.prepare_data(request.data, onboarding_request)
        
        # Log vehicle_type for debugging
        if 'vehicle_data' in nested_data:
            vehicle_type = nested_data['vehicle_data'].get('vehicle_type')
            if vehicle_type:
                logger.info(f"Vehicle type '{vehicle_type}' will be used for user {user.id}")
            else:
                logger.warning(f"No vehicle_type found in request or onboarding_request for user {user.id}")
        
        from ..serializers import RegisterFullNormalDriverSerializer
        serializer = RegisterFullNormalDriverSerializer(data=nested_data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        normal_driver = serializer.save()
        
        # Mark documents as uploaded
        onboarding_request.mark_documents_uploaded()
        
        return Response({
            'message': _('Documents uploaded successfully! Your application is now pending final review.'),
            'normal_driver_id': normal_driver.id,
            'status': 'documents_uploaded'
        }, status=status.HTTP_201_CREATED)
    
    def _handle_modification_upload(self, request, onboarding_request, user):
        """Handle partial file uploads for document modification - automatically confirms"""
        locale = get_locale(request=request)
        files_need_modification = onboarding_request.files_need_modification or []
        
        if not files_need_modification:
            message = get_bilingual_error_message(
                'No files require modification.',
                'لا توجد ملفات تحتاج إلى تعديل.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Check if driver already exists
        if not hasattr(user, 'base_driver'):
            message = get_bilingual_error_message(
                'Driver account not found. Please contact support.',
                'لم يتم العثور على حساب السائق. يرجى الاتصال بالدعم.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        base_driver = user.base_driver
        uploaded_files = []
        errors = []
        
        # Update BaseDriver files (pco, dbs, dvla)
        for file_name in ['pco', 'dbs', 'dvla']:
            if file_name in files_need_modification:
                file_obj = request.data.get(file_name)
                if not file_obj:
                    errors.append(f"{file_name.upper()} file is required.")
                    continue
                
                # Delete old file if it exists
                old_file = getattr(base_driver, file_name, None)
                if old_file:
                    try:
                        old_file.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Failed to delete old {file_name} file: {str(e)}")
                
                # Update with new file
                setattr(base_driver, file_name, file_obj)
                uploaded_files.append(file_name)
        
        # Update Vehicle files (mot, phv)
        try:
            normal_driver = base_driver.normal_driver
            vehicle = normal_driver.vehicle
            
            for file_name in ['mot', 'phv']:
                if file_name in files_need_modification:
                    file_obj = request.data.get(file_name)
                    if not file_obj:
                        errors.append(f"{file_name.upper()} file is required.")
                        continue
                    
                    # Delete old file if it exists
                    old_file = getattr(vehicle, file_name, None)
                    if old_file:
                        try:
                            old_file.delete(save=False)
                        except Exception as e:
                            logger.warning(f"Failed to delete old {file_name} file: {str(e)}")
                    
                    # Update with new file
                    setattr(vehicle, file_name, file_obj)
                    uploaded_files.append(file_name)
                    vehicle.save()
            # Ensure vehicle_type is set (from onboarding step 1) if it was missing
            if not vehicle.vehicle_type_id and onboarding_request.vehicle_type:
                from apps.vehicle.utils import get_vehicle_type_from_string
                vt = get_vehicle_type_from_string(onboarding_request.vehicle_type)
                if vt:
                    vehicle.vehicle_type = vt
                    vehicle.save(update_fields=['vehicle_type'])
                    logger.info(f"Set vehicle_type for driver {base_driver.id} from onboarding_request: {onboarding_request.vehicle_type}")
                else:
                    logger.warning(f"Could not resolve vehicle_type '{onboarding_request.vehicle_type}' for driver {base_driver.id}")
        except Exception as e:
            logger.error(f"Error updating vehicle files: {str(e)}")
            message = get_bilingual_error_message(
                'Error updating vehicle documents.',
                'خطأ في تحديث مستندات المركبة.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        if errors:
            message = get_bilingual_error_message(
                ' '.join(errors),
                ' '.join(errors),
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Save base_driver with updated files
        base_driver.save()
        
        # Automatically confirm and submit for review
        from django.db import transaction
        from django.db import connection
        import json
        with transaction.atomic():
            # Use raw SQL to update JSONField properly, avoiding serialization issues with other fields
            table_name = DriverOnboardingRequest._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {table_name} 
                    SET modification_confirmed = %s,
                        status = %s,
                        files_need_modification = %s::jsonb
                    WHERE id = %s
                    """,
                    [True, 'documents_uploaded', json.dumps([]), onboarding_request.id]
                )
            onboarding_request.refresh_from_db()
        
        # Send notification to admin that documents are ready for review
        try:
            from utils.common import notify_user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin_user in admin_users:
                try:
                    notify_user(
                        user=admin_user.id,
                        title_en='Driver Documents Ready for Review',
                        title_ar='مستندات السائق جاهزة للمراجعة',
                        desc_en=f'Driver {user.get_full_name()} has resubmitted documents for review.',
                        desc_ar=f'قام السائق {user.get_full_name()} بإعادة إرسال المستندات للمراجعة.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to admin {admin_user.id}: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to send admin notifications: {str(e)}")
        
        return Response({
            'message': _('Files uploaded and submitted for review successfully!'),
            'uploaded_files': uploaded_files,
            'status': 'documents_uploaded',
            'modification_confirmed': True
        }, status=status.HTTP_200_OK)
    
    def prepare_data(self, data, onboarding_request=None):
        """Prepare data for document upload"""
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
                "vehicle_type": data.get("vehicle_type"),  # Include vehicle_type from request
            },
            "interview_data": {
                "interview_date": data.get("interview_date"),
                "interview_time": data.get("interview_time"),
            }
        }
        
        # If vehicle_type not in request but available in onboarding_request, use it
        if not nested_data["vehicle_data"].get("vehicle_type") and onboarding_request:
            if onboarding_request.vehicle_type:
                nested_data["vehicle_data"]["vehicle_type"] = onboarding_request.vehicle_type
                logger.info(f"Using vehicle_type '{onboarding_request.vehicle_type}' from onboarding request")
        
        return remove_empty_values(nested_data)


class DriverConfirmDocumentModificationView(EMADBaseView):
    """
    Driver confirms document modification upload
    POST /api/drivers/onboarding/documents/confirm-modification/
    
    NOTE: This endpoint is now optional - files are automatically confirmed when uploaded.
    This endpoint is kept for backward compatibility and can be used to re-confirm if needed.
    """
    http_method_names = ['post']
    permission_classes = [IsAuthenticated]
    
    def handle_post(self, request):
        activate(get_locale(request=request))
        user = request.user
        locale = get_locale(request=request)
        
        try:
            onboarding_request = user.driver_onboarding_request
        except DriverOnboardingRequest.DoesNotExist:
            message = get_bilingual_error_message(
                'No onboarding request found.',
                'لم يتم العثور على طلب التسجيل.',
                locale
            )
            return create_not_found_response(message, locale)
        
        # If already confirmed and status is documents_uploaded, return success (idempotent)
        if onboarding_request.status == 'documents_uploaded' and onboarding_request.modification_confirmed:
            return Response({
                'success': True,
                'message': _('Documents are already confirmed and submitted for review.'),
                'status': 'documents_uploaded',
                'modification_confirmed': True
            }, status=status.HTTP_200_OK)
        
        if onboarding_request.status != 'needs_modification':
            message = get_bilingual_error_message(
                'No documents require modification at this time.',
                'لا توجد مستندات تحتاج إلى تعديل في الوقت الحالي.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Check if driver exists and has uploaded files
        if not hasattr(user, 'base_driver'):
            message = get_bilingual_error_message(
                'Driver account not found. Please contact support.',
                'لم يتم العثور على حساب السائق. يرجى الاتصال بالدعم.',
                locale
            )
            return create_error_response(message, locale=locale)
        
        base_driver = user.base_driver
        files_need_modification = onboarding_request.files_need_modification or []
        
        # Verify all required files have been uploaded
        missing_files = []
        for file_name in files_need_modification:
            if file_name in ['pco', 'dbs', 'dvla']:
                if not getattr(base_driver, file_name, None):
                    missing_files.append(file_name.upper())
            elif file_name in ['mot', 'phv']:
                try:
                    normal_driver = base_driver.normal_driver
                    vehicle = normal_driver.vehicle
                    if not getattr(vehicle, file_name, None):
                        missing_files.append(file_name.upper())
                except Exception:
                    missing_files.append(file_name.upper())
        
        if missing_files:
            message = get_bilingual_error_message(
                f'Please upload the following files before confirming: {", ".join(missing_files)}',
                f'يرجى رفع الملفات التالية قبل التأكيد: {", ".join(missing_files)}',
                locale
            )
            return create_error_response(message, locale=locale)
        
        # Delete old files and finalize the update
        try:
            self._delete_old_files(base_driver, files_need_modification)
        except Exception as e:
            logger.error(f"Error deleting old files: {str(e)}")
            # Continue anyway - files are already updated
        
        # Mark as confirmed and update status
        from django.db import transaction
        from django.db import connection
        import json
        with transaction.atomic():
            # Use raw SQL to update JSONField properly, avoiding serialization issues with other fields
            table_name = DriverOnboardingRequest._meta.db_table
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {table_name} 
                    SET modification_confirmed = %s,
                        status = %s,
                        files_need_modification = %s::jsonb
                    WHERE id = %s
                    """,
                    [True, 'documents_uploaded', json.dumps([]), onboarding_request.id]
                )
            onboarding_request.refresh_from_db()
        
        # Send notification to admin that documents are ready for review
        try:
            from utils.common import notify_user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin_user in admin_users:
                try:
                    notify_user(
                        user=admin_user.id,
                        title_en='Driver Documents Ready for Review',
                        title_ar='مستندات السائق جاهزة للمراجعة',
                        desc_en=f'Driver {user.get_full_name()} has resubmitted documents for review.',
                        desc_ar=f'قام السائق {user.get_full_name()} بإعادة إرسال المستندات للمراجعة.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to admin {admin_user.id}: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to send admin notifications: {str(e)}")
        
        return Response({
            'success': True,
            'message': _('Documents confirmed and submitted for review.'),
            'status': 'documents_uploaded',
            'modification_confirmed': True
        }, status=status.HTTP_200_OK)
    
    def _delete_old_files(self, base_driver, files_need_modification):
        """Delete old files that were replaced"""
        # Note: Files are already replaced in the upload step
        # This method is kept for consistency with the plan
        # In practice, old files are deleted during upload in _handle_modification_upload
        pass


class DriverOnboardingStatusView(EMADBaseView):
    """
    User can check their onboarding request status
    """
    http_method_names = ['get']
    permission_classes = [IsAuthenticated]
    
    def handle_get(self, request):
        activate(get_locale(request=request))
        user = request.user
        
        try:
            onboarding_request = user.driver_onboarding_request
        except DriverOnboardingRequest.DoesNotExist:
            return Response({
                'error': _('No onboarding request found.')
            }, status=status.HTTP_404_NOT_FOUND)
        
        from ..serializers import DriverOnboardingRequestSerializer
        serializer = DriverOnboardingRequestSerializer(onboarding_request)
        
        response_data = {
            'status': onboarding_request.status,
            'request': serializer.data,
            'next_step': self.get_next_step_message(onboarding_request.status),
            'files_need_modification': onboarding_request.files_need_modification or [],
            'modification_confirmed': onboarding_request.modification_confirmed
        }
        
        return Response(response_data)
    
    def get_next_step_message(self, status):
        """Get user-friendly message for next step"""
        messages = {
            'pending': _('Your application is being reviewed.'),
            'step1_approved': _('Step 1 approved! Please upload your documents.'),
            'step1_rejected': _('Your initial application was not approved.'),
            'documents_uploaded': _('Documents uploaded! Waiting for final review.'),
            'final_approved': _('Congratulations! You are now an approved driver.'),
            'final_rejected': _('Your application was not approved after document review.'),
            'needs_modification': _('Please modify and resubmit your documents.'),
        }
        return messages.get(status, _('Unknown status.'))


class DriverDocumentModificationStatusView(EMADBaseView):
    """
    Driver can check which files need modification
    GET /api/drivers/onboarding/documents/modification-status/
    """
    http_method_names = ['get']
    permission_classes = [IsAuthenticated]
    
    def handle_get(self, request):
        activate(get_locale(request=request))
        user = request.user
        
        try:
            onboarding_request = user.driver_onboarding_request
        except DriverOnboardingRequest.DoesNotExist:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'No onboarding request found.',
                'لم يتم العثور على طلب التسجيل.',
                locale
            )
            return create_not_found_response(message, locale)
        
        if onboarding_request.status != 'needs_modification':
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'No documents require modification at this time.',
                'لا توجد مستندات تحتاج إلى تعديل في الوقت الحالي.',
                locale
            )
            return Response({
                'error': message,
                'status': onboarding_request.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        files_need_modification = onboarding_request.files_need_modification or []
        
        # Map file names to user-friendly labels
        file_labels = {
            'pco': 'PCO License',
            'dbs': 'DBS Certificate',
            'dvla': 'DVLA License',
            'mot': 'MOT Certificate',
            'phv': 'PHV License'
        }
        
        files_with_labels = [
            {
                'file_name': file_name,
                'label': file_labels.get(file_name, file_name.upper())
            }
            for file_name in files_need_modification
        ]
        
        return Response({
            'status': onboarding_request.status,
            'files_need_modification': files_need_modification,
            'files_with_labels': files_with_labels,
            'modification_confirmed': onboarding_request.modification_confirmed,
            'rejection_reason': onboarding_request.rejection_reason,
            'message': _('Please upload the following documents: {}').format(', '.join([file_labels.get(f, f.upper()) for f in files_need_modification]))
        })


class DriverOnboardingStep3AdminView(EMADBaseView):
    """
    Step 3: Admin final review of uploaded documents
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
        
        if onboarding_request.status != 'documents_uploaded':
            locale = get_locale(request=request)
            current_status = onboarding_request.get_status_display() or onboarding_request.status
            message = get_bilingual_error_message(
                f'This request is not ready for final review. Current status: {current_status}. Expected status: Documents Uploaded.',
                f'هذا الطلب غير جاهز للمراجعة النهائية. الحالة الحالية: {current_status}. الحالة المتوقعة: تم تحميل المستندات.',
                locale
            )
            return Response({
                'error': message,
                'current_status': onboarding_request.status,
                'expected_status': 'documents_uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from ..serializers import DriverOnboardingApprovalSerializer
        serializer = DriverOnboardingApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        notes = serializer.validated_data.get('notes', '')
        rejection_reason = serializer.validated_data.get('rejection_reason', '')
        
        try:
            if action == 'approve':
                onboarding_request.approve_final(request.user, notes)
                from utils.common.email import send_driver_final_approval
                send_driver_final_approval(onboarding_request)
                
                # Send push notification to driver
                try:
                    from utils.common import notify_user
                    locale = get_locale(request=request)
                    notify_user(
                        user=onboarding_request.user.id,
                        title_en='Congratulations! You\'re Approved!',
                        title_ar='تهانينا! تمت الموافقة عليك!',
                        desc_en='Your driver onboarding has been completed successfully. You can now start accepting trips!',
                        desc_ar='تم إكمال عملية التسجيل بنجاح. يمكنك الآن البدء في قبول الرحلات!',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for final_approved: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': _('Driver onboarding completed successfully.'),
                    'status': 'final_approved'
                })
            
            elif action == 'reject':
                if not rejection_reason:
                    locale = get_locale(request=request)
                    message = get_bilingual_error_message(
                        'Rejection reason is required.',
                        'سبب الرفض مطلوب.',
                        locale
                    )
                    return create_error_response(message, locale=locale)
                
                onboarding_request.reject_final(request.user, rejection_reason)
                from utils.common.email import send_driver_final_rejection
                send_driver_final_rejection(onboarding_request, rejection_reason)
                
                # Send push notification to driver
                try:
                    from utils.common import notify_user
                    locale = get_locale(request=request)
                    notify_user(
                        user=onboarding_request.user.id,
                        title_en='Application Decision',
                        title_ar='قرار الطلب',
                        desc_en='After reviewing your documents, your application was not approved. Please check your email for details.',
                        desc_ar='بعد مراجعة مستنداتك، لم تتم الموافقة على طلبك. يرجى التحقق من بريدك الإلكتروني للتفاصيل.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for final_rejected: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': _('Driver onboarding rejected.'),
                    'status': 'final_rejected'
                })
            
            elif action == 'modify':
                if not rejection_reason:
                    locale = get_locale(request=request)
                    message = get_bilingual_error_message(
                        'Modification reason is required.',
                        'سبب التعديل مطلوب.',
                        locale
                    )
                    return create_error_response(message, locale=locale)
                
                files_to_modify = serializer.validated_data.get('files_to_modify', [])
                if not files_to_modify:
                    locale = get_locale(request=request)
                    message = get_bilingual_error_message(
                        'At least one file must be selected for modification.',
                        'يجب تحديد ملف واحد على الأقل للتعديل.',
                        locale
                    )
                    return create_error_response(message, locale=locale)
                
                onboarding_request.request_modification(request.user, rejection_reason, files_to_modify)
                from utils.common.email import send_driver_modification_request
                send_driver_modification_request(onboarding_request, rejection_reason, files_to_modify)
                
                # Send push notification to driver
                try:
                    from utils.common import notify_user
                    locale = get_locale(request=request)
                    files_list = ', '.join(files_to_modify).upper()
                    notify_user(
                        user=onboarding_request.user.id,
                        title_en='Documents Need Modification',
                        title_ar='المستندات تحتاج إلى تعديل',
                        desc_en=f'Your documents need modifications. Please update: {files_list}. Check your email for details.',
                        desc_ar=f'تحتاج مستنداتك إلى تعديلات. يرجى تحديث: {files_list}. تحقق من بريدك الإلكتروني للتفاصيل.',
                        locale=locale,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification for needs_modification: {str(e)}")
                
                return Response({
                    'success': True,
                    'message': _('Modification requested.'),
                    'status': 'needs_modification',
                    'files_to_modify': files_to_modify
                })
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing final review for request {request_id}: {str(e)}", exc_info=True)
            
            # Get locale for error message
            locale = get_locale(request=request)
            
            custom_message = get_bilingual_error_message(
                'An error occurred while processing the final review. Please try again.',
                'حدث خطأ أثناء معالجة المراجعة النهائية. يرجى المحاولة مرة أخرى.',
                locale
            )
            
            return create_exception_error_response(e, locale, custom_message)
    
