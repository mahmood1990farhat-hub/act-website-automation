from rest_framework.permissions import IsAuthenticated
from ..models import Notification
from ..serializers import NotificationSerializer
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from rest_framework import status
from utils.common import paginate_queryset
from django.utils.translation import gettext as _, activate
from utils.common import get_locale

class UserNotificationListView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def handle_get(self, request):
        locale = get_locale(request=request)
        activate(locale)
        
        # Get query parameters
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        
        # Filter notifications for current user
        queryset = Notification.objects.filter(user=request.user)
        
        # Note: Currently there's no 'is_read' field in the model
        # This can be added later if needed
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Paginate
        page_obj, paginator = paginate_queryset(queryset, request)
        
        # Serialize with request context for locale-based content
        serializer = NotificationSerializer(page_obj, many=True, context={'request': request})
        
        return Response({
            "success": True,
            "data": {
                "notifications": serializer.data,
                "pagination": {
                    "count": paginator.count,
                    "num_pages": paginator.num_pages,
                    "current_page": page_obj.number,
                    "page_size": paginator.per_page,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
