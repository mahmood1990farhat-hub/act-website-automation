from django.urls import path
from .views import * 

urlpatterns = [
    path('office-vehicle/' , OfficeVehiclesView.as_view()),
    path('office-driver/' , OfficeDriverView.as_view()),
]