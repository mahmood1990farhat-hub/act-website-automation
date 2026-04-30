from django.urls import path
from .views import (
    CreateComplaintView,
    CreateTripComplaintView,
    PassengerSubmitComplaintView,
    PassengerSubmitLostPropertyView,
    PassengerViewComplaintsView,
    PassengerViewComplaintDetailView,
    PassengerViewLostPropertyView,
    PassengerViewLostPropertyDetailView,
)

urlpatterns = [
    # Legacy endpoints
    path('create/', CreateComplaintView.as_view()),
    path('trip/create/', CreateTripComplaintView.as_view(), name='complaint-list'),

    # Passenger endpoints - Complaints
    path('passenger/complaints/submit/', PassengerSubmitComplaintView.as_view(), name='passenger_submit_complaint'),
    path('passenger/complaints/', PassengerViewComplaintsView.as_view(), name='passenger_view_complaints'),
    path('passenger/complaints/<int:complaint_id>/', PassengerViewComplaintDetailView.as_view(), name='passenger_complaint_detail'),
    
    # Passenger endpoints - Lost Property
    path('passenger/lost-property/submit/', PassengerSubmitLostPropertyView.as_view(), name='passenger_submit_lost_property'),
    path('passenger/lost-property/', PassengerViewLostPropertyView.as_view(), name='passenger_view_lost_property'),
    path('passenger/lost-property/<int:report_id>/', PassengerViewLostPropertyDetailView.as_view(), name='passenger_lost_property_detail'),
]
