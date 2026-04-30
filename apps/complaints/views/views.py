from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from utils.EMDBase import EMADBaseView  
from ..serializers import ComplaintSerializer , TripComplaintSerializer
from utils.common import remove_empty_values

class CreateComplaintView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    def handle_post(self, request):
        data = remove_empty_values(request.data)
        serializer = ComplaintSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response({"message": "Complaint created successfully"}, status=status.HTTP_201_CREATED)


class CreateTripComplaintView(EMADBaseView):
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    def handle_post(self, request):
        user = request.user
        data = remove_empty_values(request.data)
        serializer = TripComplaintSerializer(data=data , context= {'request' : request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response({"message": "Complaint created successfully"}, status=status.HTTP_201_CREATED)
        
