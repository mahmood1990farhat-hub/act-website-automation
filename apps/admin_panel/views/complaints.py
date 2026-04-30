from rest_framework.permissions import IsAdminUser
from rest_framework import status 
from rest_framework.response import Response
from django.http import HttpResponse
from utils.EMDBase import EMADBaseView
from utils.common import paginate_queryset, get_locale
from apps.complaints.models import TripComplaint, Complaint, LostProperty
from apps.complaints.serializers import (
    TripComplaintSerializer, 
    ComplaintSerializer,
    LostPropertySerializer
)
from apps.admin_panel.serializers.complaints import (
    AdminTripComplaintResponseSerializer,
    AdminLostPropertyResponseSerializer,
    AdminResolveComplaintSerializer,
    AdminResolveLostPropertySerializer
)
from apps.admin_panel.utils.pdf_generator import (
    generate_complaint_pdf,
    generate_lost_property_pdf
)
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext as _, activate
from django.utils import timezone
from utils.common.error_handlers import (
    create_error_response,
    create_not_found_response,
    create_validation_error_response,
    get_bilingual_error_message
)


class ListTripComplaintsView(EMADBaseView):
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    def handle_get(self, request):
        complaints = TripComplaint.objects.select_related(
            'user',
            'trip__passenger__user',
            'trip__base_driver__user'
        ).order_by('-created_at')

        complaint_type = request.query_params.get('complaint_type')

        if complaint_type:
            complaints = complaints.filter(complaint_type=complaint_type)
        
        resolved = request.query_params.get('resolved')
        if resolved is not None:
            if resolved.lower() == 'true':
                complaints = complaints.filter(resolved=True)
            elif resolved.lower() == 'false':
                complaints = complaints.filter(resolved=False)


        page_obj, paginator = paginate_queryset(complaints, request)
        serializer = TripComplaintSerializer(page_obj , many= True , context = {'request' : request})
        return Response({
            "complaints": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)



class ListNormalComplaintsView(EMADBaseView):
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    def handle_get(self, request):
        complaints = Complaint.objects.select_related(
            'user',
        ).order_by('-created_at')

        resolved = request.query_params.get('resolved')
        if resolved is not None:
            if resolved.lower() == 'true':
                complaints = complaints.filter(resolved=True)
            elif resolved.lower() == 'false':
                complaints = complaints.filter(resolved=False)


        page_obj, paginator = paginate_queryset(complaints, request)
        serializer = ComplaintSerializer(page_obj , many= True , context = {'request' : request})
        return Response({
            "complaints": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)



class AdminTripComplaintDetailView(EMADBaseView):
    """Admin view to get detailed information about a trip complaint"""
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request, complaint_id):
        activate(get_locale(request=request))
        try:
            complaint = get_object_or_404(
                TripComplaint.objects.select_related('user', 'trip__passenger__user', 'trip__base_driver__user'),
                id=complaint_id
            )
            serializer = TripComplaintSerializer(complaint, context={'request': request})
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'Error retrieving complaint details.',
                'خطأ في استرجاع تفاصيل الشكوى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminTripComplaintRespondView(EMADBaseView):
    """Admin view to respond to a trip complaint"""
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, complaint_id):
        activate(get_locale(request=request))
        locale = get_locale(request=request)
        
        try:
            complaint = get_object_or_404(TripComplaint, id=complaint_id)
            serializer = AdminTripComplaintResponseSerializer(data=request.data)
            
            if not serializer.is_valid():
                custom_message = get_bilingual_error_message(
                    'Error responding to complaint',
                    'خطأ في الرد على الشكوى',
                    locale
                )
                return create_validation_error_response(serializer.errors, locale, custom_message)
            
            complaint.admin_response = serializer.validated_data['admin_response']
            if 'status' in serializer.validated_data:
                complaint.status = serializer.validated_data['status']
            complaint.save()
            
            serializer = TripComplaintSerializer(complaint, context={'request': request})
            message = get_bilingual_error_message(
                'Response added successfully.',
                'تم إضافة الرد بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = get_bilingual_error_message(
                'Error responding to complaint.',
                'خطأ في الرد على الشكوى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminTripComplaintResolveView(EMADBaseView):
    """Admin view to resolve a trip complaint"""
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, complaint_id):
        activate(get_locale(request=request))
        locale = get_locale(request=request)
        
        try:
            complaint = get_object_or_404(TripComplaint, id=complaint_id)
            
            if complaint.status == 'resolved' or complaint.status == 'closed':
                message = get_bilingual_error_message(
                    'This complaint is already resolved.',
                    'تم حل هذه الشكوى بالفعل.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            serializer = AdminResolveComplaintSerializer(data=request.data)
            
            if not serializer.is_valid():
                custom_message = get_bilingual_error_message(
                    'Error resolving complaint',
                    'خطأ في حل الشكوى',
                    locale
                )
                return create_validation_error_response(serializer.errors, locale, custom_message)
            
            if 'admin_response' in serializer.validated_data:
                complaint.admin_response = serializer.validated_data['admin_response']
            complaint.status = serializer.validated_data.get('status', 'resolved')
            complaint.resolved = True
            complaint.resolved_at = timezone.now()
            complaint.save()
            
            serializer = TripComplaintSerializer(complaint, context={'request': request})
            message = get_bilingual_error_message(
                'Complaint resolved successfully.',
                'تم حل الشكوى بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = get_bilingual_error_message(
                'Error resolving complaint.',
                'خطأ في حل الشكوى.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminTripComplaintDownloadPDFView(EMADBaseView):
    """Admin view to download complaint as PDF"""
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request, complaint_id):
        try:
            complaint = get_object_or_404(
                TripComplaint.objects.select_related('user', 'trip'),
                id=complaint_id
            )
            
            buffer = generate_complaint_pdf(complaint)
            
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="complaint_{complaint.id}.pdf"'
            return response
        except Exception as e:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'Error generating PDF.',
                'خطأ في إنشاء ملف PDF.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========== LOST PROPERTY ADMIN VIEWS ==========

class AdminLostPropertyListView(EMADBaseView):
    """Admin view to list all lost property reports"""
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request):
        activate(get_locale(request=request))
        lost_properties = LostProperty.objects.select_related(
            'user',
            'trip__passenger__user'
        ).order_by('-created_at')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            lost_properties = lost_properties.filter(status=status_filter)
        
        # Filter by item type
        item_type = request.query_params.get('item_type')
        if item_type:
            lost_properties = lost_properties.filter(item_type=item_type)
        
        # Filter by trip
        trip_id = request.query_params.get('trip_id')
        if trip_id:
            lost_properties = lost_properties.filter(trip_id=trip_id)
        
        page_obj, paginator = paginate_queryset(lost_properties, request)
        serializer = LostPropertySerializer(page_obj, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'count': paginator.count,
                'num_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)


class AdminLostPropertyDetailView(EMADBaseView):
    """Admin view to get detailed information about a lost property report"""
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request, lost_property_id):
        activate(get_locale(request=request))
        try:
            lost_property = get_object_or_404(
                LostProperty.objects.select_related('user', 'trip__passenger__user'),
                id=lost_property_id
            )
            serializer = LostPropertySerializer(lost_property, context={'request': request})
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'Error retrieving lost property details.',
                'خطأ في استرجاع تفاصيل المفقودات.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLostPropertyRespondView(EMADBaseView):
    """Admin view to respond to a lost property report"""
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, lost_property_id):
        activate(get_locale(request=request))
        locale = get_locale(request=request)
        
        try:
            lost_property = get_object_or_404(LostProperty, id=lost_property_id)
            serializer = AdminLostPropertyResponseSerializer(data=request.data)
            
            if not serializer.is_valid():
                custom_message = get_bilingual_error_message(
                    'Error responding to lost property report',
                    'خطأ في الرد على تقرير المفقودات',
                    locale
                )
                return create_validation_error_response(serializer.errors, locale, custom_message)
            
            lost_property.admin_notes = serializer.validated_data['admin_notes']
            if 'status' in serializer.validated_data:
                lost_property.status = serializer.validated_data['status']
            lost_property.save()
            
            serializer = LostPropertySerializer(lost_property, context={'request': request})
            message = get_bilingual_error_message(
                'Response added successfully.',
                'تم إضافة الرد بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = get_bilingual_error_message(
                'Error responding to lost property report.',
                'خطأ في الرد على تقرير المفقودات.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLostPropertyResolveView(EMADBaseView):
    """Admin view to resolve a lost property report"""
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    
    def handle_post(self, request, lost_property_id):
        activate(get_locale(request=request))
        locale = get_locale(request=request)
        
        try:
            lost_property = get_object_or_404(LostProperty, id=lost_property_id)
            
            if lost_property.status in ['returned', 'closed', 'not_found']:
                message = get_bilingual_error_message(
                    'This lost property report is already resolved.',
                    'تم حل تقرير المفقودات هذا بالفعل.',
                    locale
                )
                return create_error_response(message, locale=locale, status_code=status.HTTP_400_BAD_REQUEST)
            
            serializer = AdminResolveLostPropertySerializer(data=request.data)
            
            if not serializer.is_valid():
                custom_message = get_bilingual_error_message(
                    'Error resolving lost property report',
                    'خطأ في حل تقرير المفقودات',
                    locale
                )
                return create_validation_error_response(serializer.errors, locale, custom_message)
            
            if 'admin_notes' in serializer.validated_data:
                lost_property.admin_notes = serializer.validated_data['admin_notes']
            
            new_status = serializer.validated_data.get('status', 'found')
            lost_property.status = new_status
            
            if new_status == 'found':
                lost_property.found_at = timezone.now()
            elif new_status == 'returned':
                lost_property.returned_at = timezone.now()
            
            lost_property.save()
            
            serializer = LostPropertySerializer(lost_property, context={'request': request})
            message = get_bilingual_error_message(
                'Lost property report resolved successfully.',
                'تم حل تقرير المفقودات بنجاح.',
                locale
            )
            
            return Response({
                'success': True,
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            message = get_bilingual_error_message(
                'Error resolving lost property report.',
                'خطأ في حل تقرير المفقودات.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLostPropertyDownloadPDFView(EMADBaseView):
    """Admin view to download lost property report as PDF"""
    http_method_names = ['get']
    permission_classes = [IsAdminUser]
    
    def handle_get(self, request, lost_property_id):
        try:
            lost_property = get_object_or_404(
                LostProperty.objects.select_related('user', 'trip'),
                id=lost_property_id
            )
            
            buffer = generate_lost_property_pdf(lost_property)
            
            response = HttpResponse(buffer.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="lost_property_{lost_property.id}.pdf"'
            return response
        except Exception as e:
            locale = get_locale(request=request)
            message = get_bilingual_error_message(
                'Error generating PDF.',
                'خطأ في إنشاء ملف PDF.',
                locale
            )
            return create_error_response(message, locale=locale, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Keep old resolve view for backward compatibility
class ResolveComplaintView(EMADBaseView):
    http_method_names = ['post']
    permission_classes = [IsAdminUser]
    def handle_post(self, request , complaint_id):
        activate(get_locale(request=request))
        complaint_type = request.query_params.get('type')
        if complaint_type == 'normal_complaint':
            complaint  = get_object_or_404(Complaint , id = complaint_id)
        elif complaint_type == 'trip_complaint':
            complaint = get_object_or_404(TripComplaint , id= complaint_id)
        else:
            raise ValidationError({'details' : "Invalid trip's type"})
        if complaint.resolved:
            raise ValidationError({'details' : 'This complaint is already resolved'})
        
        complaint.resolved = True 
        complaint.save()
        return Response({'message' : _('Trip marked as solved')} , status=status.HTTP_200_OK)