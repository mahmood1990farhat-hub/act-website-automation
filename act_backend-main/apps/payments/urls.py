from django.urls import path

from .views.views import booking_status_view, stripe_webhook_view
from .cancellation_views import CancellationReconcileView
from .cancellation_operator import CancellationQueueView, CancellationOperatorReviewView

urlpatterns = [
    path('booking-status/', booking_status_view),
    path('webhook/stripe/', stripe_webhook_view),
    path('cancellations/', CancellationQueueView.as_view()),
    path('cancellations/<uuid:receipt_id>/review/', CancellationOperatorReviewView.as_view()),
    path('cancellations/<uuid:receipt_id>/reconcile/', CancellationReconcileView.as_view()),
]
