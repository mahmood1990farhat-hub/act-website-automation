from rest_framework import generics
from ..models import VehicleType
from ..serializers import VehicleTypeSerializer


class VehicleTypeListAPIView(generics.ListAPIView):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer
