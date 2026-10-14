from django.urls import path
from .views import * 
from .views.onboarding_step2_views import (
    DriverOnboardingStep2View as Step2View, DriverOnboardingStatusView, 
    DriverOnboardingStep3AdminView, DriverDocumentModificationStatusView,
    DriverConfirmDocumentModificationView
)
from .views.driver_login_views import DriverLoginView, DriverOnboardingDashboardView
from .views.unified_application import (
    UnifiedDriverApplicationView, UnifiedDriverSetPasswordView,
    UnifiedDriverResendLinkView, PrivateDriverApplicationDocumentView,
    UnifiedDriverVehicleSupplementView, UnifiedDriverCorrectionView,
)
from .views.unified_admin import (
    AdminUnifiedApplicationDetailView, AdminUnifiedApplicationDecisionView,
)
from .views.operator_lifecycle import (
    AdminUnifiedDriverCeaseView, AdminUnifiedVehicleReplaceView,
    AdminUnifiedVehicleEvidenceView, AdminOperatorNIInspectionView,
)

urlpatterns = [
    # Legacy endpoints (deprecated)
    path('create-normal-driver-account/', CreateNormalDriverAccountView.as_view()), #checked
    path('complete-normal-driver-info/', CompleteNormalDriverInfoView.as_view()), #checked
    path('update-normal-driver-info/' , UpdateNormalDriverInfoView.as_view()),#checked
    
    # Unified onboarding for new applicants. Legacy step1/step2 still work
    # for applications already in progress (no data migration/cutover).
    path('onboarding/apply/', UnifiedDriverApplicationView.as_view(), name='unified_driver_apply'),
    path('onboarding/set-password/', UnifiedDriverSetPasswordView.as_view(), name='unified_driver_set_password'),
    path('onboarding/add-vehicle/', UnifiedDriverVehicleSupplementView.as_view(),
         name='unified_driver_add_vehicle'),
    path('onboarding/correct/', UnifiedDriverCorrectionView.as_view(),
         name='unified_driver_correct'),
    path('onboarding/resend-password-link/', UnifiedDriverResendLinkView.as_view(), name='unified_driver_resend_link'),
    path('admin/unified-documents/<int:document_id>/', PrivateDriverApplicationDocumentView.as_view(),
         name='admin_private_driver_document'),
    path('admin/unified-applications/<int:request_id>/', AdminUnifiedApplicationDetailView.as_view(),
         name='admin_unified_application_detail'),
    path('admin/unified-applications/<int:request_id>/decision/', AdminUnifiedApplicationDecisionView.as_view(),
         name='admin_unified_application_decision'),

    # Approved unified driver and vehicle lifecycle (admin only).
    path('admin/unified-applications/<int:request_id>/cease/', AdminUnifiedDriverCeaseView.as_view(),
         name='admin_unified_cease_availability'),
    path('admin/unified-applications/<int:request_id>/replace-vehicle/', AdminUnifiedVehicleReplaceView.as_view(),
         name='admin_unified_vehicle_replace'),
    path('admin/unified-vehicle-evidence/<int:document_id>/', AdminUnifiedVehicleEvidenceView.as_view(),
         name='admin_unified_vehicle_evidence'),
    path('admin/unified-applications/<int:request_id>/ni-inspection/', AdminOperatorNIInspectionView.as_view(),
         name='admin_unified_ni_inspection'),

    # New three-step onboarding flow
    path('onboarding/step1/', DriverOnboardingStep1View.as_view(), name='driver_onboarding_step1'),
    path('onboarding/step2/', Step2View.as_view(), name='driver_onboarding_step2'),
    path('onboarding/status/', DriverOnboardingStatusView.as_view(), name='driver_onboarding_status'),
    path('onboarding/documents/modification-status/', DriverDocumentModificationStatusView.as_view(), name='driver_document_modification_status'),
    path('onboarding/documents/confirm-modification/', DriverConfirmDocumentModificationView.as_view(), name='driver_confirm_document_modification'),
    
    # Driver login and dashboard
    path('login/', DriverLoginView.as_view(), name='driver_login'),
    path('dashboard/', DriverOnboardingDashboardView.as_view(), name='driver_dashboard'),
    
    # Admin endpoints for reviewing onboarding requests
    path('admin/onboarding-requests/', AdminOnboardingRequestsListView.as_view(), name='admin_onboarding_requests'),
    path('admin/onboarding-requests/<int:request_id>/', AdminOnboardingRequestDetailView.as_view(), name='admin_onboarding_request_detail'),
    path('admin/onboarding-requests/<int:request_id>/action/', AdminOnboardingRequestActionView.as_view(), name='admin_onboarding_request_action'),
    path('admin/onboarding-requests/<int:request_id>/final-review/', DriverOnboardingStep3AdminView.as_view(), name='admin_onboarding_final_review'),
    
    # Other endpoints
    path("trip-stats/", DriverTripStatsView.as_view()),#checked
    
    # Stripe Connect (create Express account + onboarding link for driver payouts)
    path('stripe-connect/create/', CreateStripeConnectAccountView.as_view()),
    path('stripe/connect/', CreateStripeConnectAccountView.as_view()),  # Alternate path
]