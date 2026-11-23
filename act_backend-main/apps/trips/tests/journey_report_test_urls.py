"""Only existing journey/detail views; no payment or external-service routes."""

from django.urls import path

from apps.trips.views.driver_trips import DriverTripDetailView
from apps.trips.views.end_trip import CompleteTripView
from apps.trips.views.start_trip import StartTripView


urlpatterns = [
    path("api/driver/trips/<int:trip_id>/", DriverTripDetailView.as_view()),
    path("api/trips/<int:trip_id>/start/", StartTripView.as_view()),
    path("api/trips/<int:trip_id>/complete/", CompleteTripView.as_view()),
]
