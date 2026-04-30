from .driver_registrations import CreateNormalDriverAccountView , CompleteNormalDriverInfoView , UpdateNormalDriverInfoView
from .trip_statistics import DriverTripStatsView
from .onboarding_views import (
    DriverOnboardingStep1View,
    DriverOnboardingStep2View,
    AdminOnboardingRequestsListView,
    AdminOnboardingRequestDetailView,
    AdminOnboardingRequestActionView
)
from .stripe_connect import CreateStripeConnectAccountView