from django.urls import path
from .views.earnings_views import DriverEarningsView
from .views.payout_views import DriverPayoutRequestView

urlpatterns = [
    path('earnings/', DriverEarningsView.as_view(), name='driver_earnings'),
    path('payouts/request/', DriverPayoutRequestView.as_view(), name='driver_payout_request'),
]

