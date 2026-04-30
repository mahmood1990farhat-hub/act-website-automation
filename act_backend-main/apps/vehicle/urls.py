from django.urls import path
from .views import * 
urlpatterns = [
    path('vehicle-types/', VehicleTypeListAPIView.as_view(), name='vehicle-types'),
]