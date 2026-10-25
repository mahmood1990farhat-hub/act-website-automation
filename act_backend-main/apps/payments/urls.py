from django.urls import path

from .views.views import booking_status_view, stripe_webhook_view
from .cancellation_views import CancellationReviewView, CancellationReconcileView

urlpatterns = [
    path('booking-status/', booking_status_view),
    path('webhook/stripe/', stripe_webhook_view),
    path('cancellations/<uuid:receipt_id>/review/', CancellationReviewView.as_view()),
    path('cancellations/<uuid:receipt_id>/reconcile/', CancellationReconcileView.as_view()),
]
