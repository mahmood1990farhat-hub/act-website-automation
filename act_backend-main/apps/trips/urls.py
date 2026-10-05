from django.urls import path
from .views import * 
from .views.initiate_payment import InitiateGuestPaymentView
from .views.download_confirmation import download_booking_confirmation


urlpatterns = [
    path('booking-confirmation/<uuid:token>/', download_booking_confirmation, name='download-booking-confirmation'),
    path('calculate-trip-cost/' , CalculateTripCostView.as_view()), 
    path('initiate-payment/', InitiatePaymentView.as_view()),
    path('initiate-guest-payment/', InitiateGuestPaymentView.as_view()),
    path('create-trip/' , CreateTripView.as_view()),   
    path('<int:trip_id>/accept/', AcceptTripAPIView.as_view()), 
    path('<int:trip_id>/driver-on-the-way/' , MarkDriverOnTheWayView.as_view()),
    path("<int:trip_id>/start/", StartTripView.as_view(), name="start_trip"),
    path('<int:trip_id>/complete/', CompleteTripView.as_view()), 
    path('<int:trip_id>/cancel/', PassengerCancelTripView.as_view()),
    path('<int:trip_id>/driver-cancel/', DriverCancelTripView.as_view()),
    path('list-trips/', UserTripsListView.as_view(), name='user-trips'), 
    path('list-airports/' , ListAirportView.as_view()),
    path('latest-trips/' , LatestCompletedTripView.as_view()),
    path('new-trip-requests/' , NewTripRequestsView.as_view()),

]
