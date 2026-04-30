from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import NotFound
from utils.EMDBase import EMADBaseView
from apps.accounts.permissions import IsPassenger, IsVerifiedAndProfileCompleted
from ..serializers import TripComplaintSerializer, LostPropertySerializer
from ..models import TripComplaint, LostProperty
from utils.common import remove_empty_values, paginate_queryset
from django.db.models import Q


class PassengerSubmitComplaintView(EMADBaseView):
    """
    Passenger submits a complaint about a trip
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['post']

    def handle_post(self, request):
        data = remove_empty_values(request.data)
        serializer = TripComplaintSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save(user=request.user)
        
        return Response({
            "success": True,
            "message": "Complaint submitted successfully",
            "data": {
                "complaint_id": complaint.id,
                "ticket_number": f"COMP-{complaint.id:06d}",
                "status": complaint.status,
                "status_display": complaint.get_status_display(),
                "created_at": complaint.created_at.isoformat()
            }
        }, status=status.HTTP_201_CREATED)


class PassengerSubmitLostPropertyView(EMADBaseView):
    """
    Passenger submits a lost property report for a trip
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['post']

    def handle_post(self, request):
        data = remove_empty_values(request.data)
        serializer = LostPropertySerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        lost_property = serializer.save(user=request.user)
        
        return Response({
            "success": True,
            "message": "Lost property report submitted successfully",
            "data": {
                "report_id": lost_property.id,
                "ticket_number": f"LOST-{lost_property.id:06d}",
                "status": lost_property.status,
                "status_display": lost_property.get_status_display(),
                "created_at": lost_property.created_at.isoformat()
            }
        }, status=status.HTTP_201_CREATED)


class PassengerViewComplaintsView(EMADBaseView):
    """
    Passenger views their complaints/tickets with status
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['get']

    def handle_get(self, request):
        user = request.user
        
        # Get filter parameters
        status_filter = request.query_params.get('status')
        complaint_type = request.query_params.get('complaint_type')
        trip_id = request.query_params.get('trip_id')
        
        # Build queryset
        queryset = TripComplaint.objects.filter(user=user).select_related(
            'trip',
            'trip__passenger__user',
            'trip__base_driver__user'
        ).order_by('-created_at')
        
        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if complaint_type:
            queryset = queryset.filter(complaint_type=complaint_type)
        
        if trip_id:
            try:
                queryset = queryset.filter(trip_id=int(trip_id))
            except (ValueError, TypeError):
                pass
        
        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = TripComplaintSerializer(page_obj, many=True, context={'request': request})
        
        # Get statistics
        stats = {
            'total': TripComplaint.objects.filter(user=user).count(),
            'pending': TripComplaint.objects.filter(user=user, status='pending').count(),
            'under_review': TripComplaint.objects.filter(user=user, status='under_review').count(),
            'resolved': TripComplaint.objects.filter(user=user, status='resolved').count(),
            'closed': TripComplaint.objects.filter(user=user, status='closed').count(),
        }
        
        return Response({
            "success": True,
            "data": {
                "complaints": serializer.data,
                "stats": stats,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page_obj.number if hasattr(page_obj, 'number') else 1,
                    "page_size": paginator.per_page,
                }
            }
        }, status=status.HTTP_200_OK)


class PassengerViewComplaintDetailView(EMADBaseView):
    """
    Passenger views detailed information about a specific complaint
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['get']

    def handle_get(self, request, complaint_id):
        try:
            complaint = TripComplaint.objects.select_related(
                'trip',
                'trip__passenger__user',
                'trip__base_driver__user'
            ).get(id=complaint_id, user=request.user)
        except TripComplaint.DoesNotExist:
            raise NotFound("Complaint not found")
        
        serializer = TripComplaintSerializer(complaint, context={'request': request})
        
        return Response({
            "success": True,
            "data": {
                "complaint": serializer.data,
                "ticket_number": f"COMP-{complaint.id:06d}"
            }
        }, status=status.HTTP_200_OK)


class PassengerViewLostPropertyView(EMADBaseView):
    """
    Passenger views their lost property reports with status
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['get']

    def handle_get(self, request):
        user = request.user
        
        # Get filter parameters
        status_filter = request.query_params.get('status')
        item_type = request.query_params.get('item_type')
        trip_id = request.query_params.get('trip_id')
        
        # Build queryset
        queryset = LostProperty.objects.filter(user=user).select_related(
            'trip',
            'trip__passenger__user',
            'trip__base_driver__user'
        ).order_by('-created_at')
        
        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        if trip_id:
            try:
                queryset = queryset.filter(trip_id=int(trip_id))
            except (ValueError, TypeError):
                pass
        
        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = LostPropertySerializer(page_obj, many=True, context={'request': request})
        
        # Get statistics
        stats = {
            'total': LostProperty.objects.filter(user=user).count(),
            'reported': LostProperty.objects.filter(user=user, status='reported').count(),
            'under_investigation': LostProperty.objects.filter(user=user, status='under_investigation').count(),
            'found': LostProperty.objects.filter(user=user, status='found').count(),
            'returned': LostProperty.objects.filter(user=user, status='returned').count(),
            'not_found': LostProperty.objects.filter(user=user, status='not_found').count(),
            'closed': LostProperty.objects.filter(user=user, status='closed').count(),
        }
        
        return Response({
            "success": True,
            "data": {
                "lost_property_reports": serializer.data,
                "stats": stats,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page_obj.number if hasattr(page_obj, 'number') else 1,
                    "page_size": paginator.per_page,
                }
            }
        }, status=status.HTTP_200_OK)


class PassengerViewLostPropertyDetailView(EMADBaseView):
    """
    Passenger views detailed information about a specific lost property report
    """
    permission_classes = [IsPassenger, IsVerifiedAndProfileCompleted]
    http_method_names = ['get']

    def handle_get(self, request, report_id):
        try:
            lost_property = LostProperty.objects.select_related(
                'trip',
                'trip__passenger__user',
                'trip__base_driver__user'
            ).get(id=report_id, user=request.user)
        except LostProperty.DoesNotExist:
            raise NotFound("Lost property report not found")
        
        serializer = LostPropertySerializer(lost_property, context={'request': request})
        
        return Response({
            "success": True,
            "data": {
                "lost_property": serializer.data,
                "ticket_number": f"LOST-{lost_property.id:06d}"
            }
        }, status=status.HTTP_200_OK)

