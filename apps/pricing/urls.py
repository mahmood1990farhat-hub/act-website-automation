from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import (
    PricingSettingsViewSet,
    PricingTierViewSet,
    PeakTimeRuleViewSet,
    AirportFeeViewSet
)

router = DefaultRouter()
# Register other ViewSets
router.register(r'tiers', PricingTierViewSet, basename='pricing-tier')
router.register(r'peak-rules', PeakTimeRuleViewSet, basename='peak-time-rule')
router.register(r'airport-fees', AirportFeeViewSet, basename='airport-fee')

# Custom URL patterns for singleton settings (works with or without ID)
urlpatterns = [
    # Singleton settings - PUT/PATCH work on /settings/ or /settings/1/
    path('settings/', PricingSettingsViewSet.as_view({
        'get': 'list',
        'put': 'update',
        'patch': 'partial_update'
    }), name='pricing-settings'),
    path('settings/<int:pk>/', PricingSettingsViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    }), name='pricing-settings-detail'),
] + router.urls

