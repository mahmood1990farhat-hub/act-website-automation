from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser, AllowAny
from utils.EMDBase import EMADBaseView
from apps.admin_panel.models.instruction_files import InstructionFile
from apps.admin_panel.serializers.instruction_files import InstructionFileSerializer, InstructionFilePublicSerializer
from utils.common import get_locale, paginate_queryset
from utils.common.error_handlers import create_error_response, get_bilingual_error_message
from django.utils.translation import activate
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
import logging

logger = logging.getLogger(__name__)


class InstructionFileListView(EMADBaseView):
    """
    List all instruction files or create a new one (Admin only)
    GET /api/admin-panel/instruction-files/
    POST /api/admin-panel/instruction-files/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'post']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        file_type_filter = request.query_params.get('file_type')
        is_active_filter = request.query_params.get('is_active')
        
        queryset = InstructionFile.objects.select_related('created_by', 'updated_by').order_by('-updated_at')
        
        if file_type_filter:
            queryset = queryset.filter(file_type=file_type_filter.upper())
        if is_active_filter is not None:
            is_active = is_active_filter.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = InstructionFileSerializer(page_obj, many=True, context={'request': request})
        
        return Response({
            "success": True,
            "data": {
                "instruction_files": serializer.data,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page_obj.number if hasattr(page_obj, 'number') else 1,
                    "page_size": paginator.per_page,
                }
            }
        }, status=status.HTTP_200_OK)
    
    def handle_post(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        serializer = InstructionFileSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            message = get_bilingual_error_message(
                'Invalid data provided',
                'البيانات المقدمة غير صالحة',
                locale
            )
            return create_error_response(
                message,
                errors=serializer.errors,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if file_type already exists
        file_type = serializer.validated_data.get('file_type')
        if InstructionFile.objects.filter(file_type=file_type).exists():
            message = get_bilingual_error_message(
                f'Instruction file with type {file_type} already exists. Use update endpoint instead.',
                f'ملف التعليمات من نوع {file_type} موجود بالفعل. استخدم نقطة التحديث بدلاً من ذلك.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            instruction_file = serializer.save(
                created_by=request.user,
                updated_by=request.user
            )
        
        logger.info(f"Admin {request.user.id} created instruction file: {file_type}")
        
        message = get_bilingual_error_message(
            'Instruction file created successfully',
            'تم إنشاء ملف التعليمات بنجاح',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": InstructionFileSerializer(instruction_file, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class InstructionFileDetailView(EMADBaseView):
    """
    Update or delete an instruction file (Admin only)
    PUT/PATCH /api/admin-panel/instruction-files/<file_id>/
    DELETE /api/admin-panel/instruction-files/<file_id>/
    """
    permission_classes = [IsAdminUser]
    http_method_names = ['put', 'patch', 'delete']
    
    def handle_put(self, request, file_id):
        return self._handle_update(request, file_id, partial=False)
    
    def handle_patch(self, request, file_id):
        return self._handle_update(request, file_id, partial=True)
    
    def handle_delete(self, request, file_id):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            instruction_file = InstructionFile.objects.get(id=file_id)
        except InstructionFile.DoesNotExist:
            message = get_bilingual_error_message(
                'Instruction file not found',
                'ملف التعليمات غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
        
        file_type = instruction_file.file_type
        instruction_file.delete()
        
        logger.info(f"Admin {request.user.id} deleted instruction file {file_id} ({file_type})")
        
        message = get_bilingual_error_message(
            'Instruction file deleted successfully',
            'تم حذف ملف التعليمات بنجاح',
            locale
        )
        return Response({
            "success": True,
            "message": message
        }, status=status.HTTP_200_OK)
    
    def _handle_update(self, request, file_id, partial=False):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            instruction_file = InstructionFile.objects.get(id=file_id)
        except InstructionFile.DoesNotExist:
            message = get_bilingual_error_message(
                'Instruction file not found',
                'ملف التعليمات غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
        
        serializer = InstructionFileSerializer(
            instruction_file,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            message = get_bilingual_error_message(
                'Invalid data provided',
                'البيانات المقدمة غير صالحة',
                locale
            )
            return create_error_response(
                message,
                errors=serializer.errors,
                locale=locale,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if file_type is being changed and if new type already exists
        if 'file_type' in serializer.validated_data:
            new_file_type = serializer.validated_data['file_type']
            if new_file_type != instruction_file.file_type:
                if InstructionFile.objects.filter(file_type=new_file_type).exclude(id=file_id).exists():
                    message = get_bilingual_error_message(
                        f'Instruction file with type {new_file_type} already exists',
                        f'ملف التعليمات من نوع {new_file_type} موجود بالفعل',
                        locale
                    )
                    return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Track if file is being updated (for version increment)
            old_file = instruction_file.file
            instruction_file = serializer.save(updated_by=request.user)
            
            # Version is auto-incremented in model save() if file changed
        
        logger.info(f"Admin {request.user.id} updated instruction file {file_id}")
        
        message = get_bilingual_error_message(
            'Instruction file updated successfully',
            'تم تحديث ملف التعليمات بنجاح',
            locale
        )
        return Response({
            "success": True,
            "message": message,
            "data": InstructionFileSerializer(instruction_file, context={'request': request}).data
        }, status=status.HTTP_200_OK)




class InstructionFilePublicListView(EMADBaseView):
    """
    Get all active instruction files (Public - No auth required)
    GET /api/instruction-files/
    """
    permission_classes = [AllowAny]
    http_method_names = ['get']
    
    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        file_type_filter = request.query_params.get('file_type')
        
        queryset = InstructionFile.objects.filter(is_active=True).order_by('-updated_at')
        
        if file_type_filter:
            queryset = queryset.filter(file_type=file_type_filter.upper())
        
        serializer = InstructionFilePublicSerializer(queryset, many=True, context={'request': request})
        
        return Response({
            "success": True,
            "data": {
                "instruction_files": serializer.data
            }
        }, status=status.HTTP_200_OK)


class InstructionFilePublicDetailView(EMADBaseView):
    """
    Get a specific instruction file by type (Public - No auth required)
    GET /api/instruction-files/<file_type>/
    """
    permission_classes = [AllowAny]
    http_method_names = ['get']
    
    def handle_get(self, request, file_type):
        locale = get_locale(request=request)
        activate(locale)
        
        try:
            instruction_file = InstructionFile.objects.get(
                file_type=file_type.upper(),
                is_active=True
            )
        except InstructionFile.DoesNotExist:
            message = get_bilingual_error_message(
                'Instruction file not found',
                'ملف التعليمات غير موجود',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_404_NOT_FOUND)
        
        serializer = InstructionFilePublicSerializer(instruction_file, context={'request': request})
        
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
