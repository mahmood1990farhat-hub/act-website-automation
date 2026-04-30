from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from utils.common import validate_int_value , get_locale , paginate_queryset
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import IsPassenger , IsVerifiedAndProfileCompleted, IsNormalDriver
from ..models import Trip 
from django.utils.translation import gettext as _ , activate
from ..serializers import TripSerializer ,  TripWithStopPointSerializer
from apps.passengers.models import Passenger
from django.utils import timezone
from django.db.models import Q
from utils.common.error_handlers import (
    get_bilingual_error_message
)


class UserTripsListView(EMADBaseView):
    permission_classes = [IsVerifiedAndProfileCompleted]
    http_method_names = ['get']

    def get_queryset(self, request):
        activate(get_locale(request=request))
        user = request.user
        account_type = user.account_type
        trip_status_param = request.query_params.get('trip_status')

        if account_type == 'passenger':
            queryset = Trip.objects.filter(passenger__user=user).select_related(
                'base_driver__user',
                'base_driver__normal_driver__vehicle',
                'guest_driver_car',
                'airport',
            )

        elif account_type == 'normal_driver':
            # Include trips assigned to this driver OR trips cancelled by this driver
            from apps.drivers.models import BaseDriver
            try:
                base_driver = BaseDriver.objects.get(user=user)
                queryset = Trip.objects.filter(
                    Q(base_driver=base_driver) | Q(cancelled_by_driver_id=base_driver)
                ).select_related(
                    'passenger__user',
                    'airport'
                )
            except BaseDriver.DoesNotExist:
                queryset = Trip.objects.none()

        else:
            raise ValidationError({"detail": _('Unsupported account type')})

        if trip_status_param:
            trip_statuses = trip_status_param.split(',')
            allowed_statuses = ['pending', 'active', 'driver_on_the_way', 'accepted', 'completed', 'cancelled']
            
            invalid_statuses = [status for status in trip_statuses if status not in allowed_statuses]
            if invalid_statuses:
                raise ValidationError({"trip_status": _(f"Invalid trip status: {', '.join(invalid_statuses)}")})
            
            queryset = queryset.filter(status__in=trip_statuses)

        queryset = queryset.prefetch_related('stop_points')

        return queryset


    def handle_get(self, request):
        trip_id = request.query_params.get('trip_id')
        user = request.user

        if trip_id:
            validate_int_value(trip_id , field_name='trip_id' , required=True)
            try:
                trip = self.get_queryset(request).get(id=trip_id)
            except Trip.DoesNotExist:
                raise ValidationError({"trip_id": _("Trip not found or not accessible")})
            serializer = TripWithStopPointSerializer(
                trip,
                context={'request': request, 'account_type': user.account_type},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        queryset = self.get_queryset(request).order_by("-created_at")
        page_obj, paginator = paginate_queryset(queryset, request)
        serializer = TripWithStopPointSerializer(page_obj, many=True , context= {'request': request , 'account_type': user.account_type})
        
        return Response({
            "trips": serializer.data,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)




class LatestCompletedTripView(EMADBaseView):
    permission_classes = [IsPassenger]
    def handle_get(self, request):
        try:
            passenger = request.user.passenger_profile
        except Passenger.DoesNotExist:
            raise ValidationError({"details" : "Passenger profile not found."})


        time_threshold = timezone.now() - timezone.timedelta(hours=24)

        latest_trip = (
            Trip.objects.filter(
                passenger=passenger,
                status="completed",
                created_at__gte=time_threshold
            )
            .order_by("-created_at")
        )

        serializer = TripSerializer(latest_trip , many = True)
        return Response(serializer.data)


        

