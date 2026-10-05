from django.urls import path

from .views.views import booking_status_view, stripe_webhook_view

urlpatterns = [
    path('booking-status/', booking_status_view),
    path('webhook/stripe/', stripe_webhook_view),
]
