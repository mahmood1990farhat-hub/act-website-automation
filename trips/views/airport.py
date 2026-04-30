from rest_framework import status
from rest_framework.response import Response
from utils.EMDBase import EMADBaseView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from ..models import Airport
from ..serializers import AirportSerializer

class ListAirportView(EMADBaseView):
    permission_classes = [AllowAny]
    def handle_get(self, request):
        airports = Airport.objects.all()
        serializer = AirportSerializer(airports , many = True , context = {'request' : request})
        return Response(serializer.data , status=status.HTTP_200_OK)
        


