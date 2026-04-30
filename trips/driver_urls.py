from django.urls import path
from .views import (
    DriverTripsListView,
    DriverTripDetailView
)

urlpatterns = [
    path('trips/', DriverTripsListView.as_view(), name='driver-trips-list'),
    path('trips/<int:trip_id>/', DriverTripDetailView.as_view(), name='driver-trip-detail'),
]

