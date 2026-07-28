from django.urls import path

from .views.views import stripe_webhook_view

urlpatterns = [
    path('webhook/stripe/', stripe_webhook_view),
]
