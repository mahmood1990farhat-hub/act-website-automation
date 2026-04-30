from django.urls import path
from .views import * 
urlpatterns = [
    path('webhook/stripe/', stripe_webhook_view),
]