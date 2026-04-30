from django.urls import path
from .views import * 

urlpatterns = [
    path('register-passenger/' , RegisterPassengerView.as_view()), #checked
    path('update-profile/' , UpdatePassengerView.as_view()), #checked


]