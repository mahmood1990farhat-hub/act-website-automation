from utils.EMDBase import EMADBaseView
from rest_framework.response import Response
from apps.accounts.permissions import IsNormalDriver , IsVerifiedAndProfileCompleted
from django.db.models import Count
from apps.trips.models import Trip
from ..models import NormalDriver


class DriverTripStatsView(EMADBaseView):
    permission_classes = [IsNormalDriver , IsVerifiedAndProfileCompleted]

    def handle_get(self, request):
        try:
            normal_driver = NormalDriver.objects.get(driver__user=request.user)
        except NormalDriver.DoesNotExist:
            return Response({"error": "Normal driver profile not found."}, status=404)

        base_driver = normal_driver.driver

        trip_counts = Trip.objects.filter(base_driver=base_driver)\
            .values('status')\
            .annotate(count=Count('id'))

        stats = {
            "pending": 0,
            "accepted": 0,
            "up_comming": 0,
            "active": 0,
            "completed": 0,
            "cancelled": 0
        }

        for item in trip_counts:
            stats[item["status"]] = item["count"]

        return Response(stats)


        





