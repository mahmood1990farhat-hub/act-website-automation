from django.urls import path
from .views import (
    PassengerTripsListView,
    PassengerTripDetailView,
    PassengerCancelTripView
)

urlpatterns = [
    path('trips/', PassengerTripsListView.as_view(), name='passenger-trips-list'),
    path('trips/<int:trip_id>/', PassengerTripDetailView.as_view(), name='passenger-trip-detail'),
    path('trips/<int:trip_id>/cancel/', PassengerCancelTripView.as_view(), name='passenger-trip-cancel'),
]

