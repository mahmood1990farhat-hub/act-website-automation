from django.urls import path 
from .views import *


urlpatterns = [
    path('login/', LoginView.as_view()), #checked
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'), #checked
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),#checked
    path('notifications/', UserNotificationListView.as_view()),#checked
    path('logout/', LogoutView.as_view()), #checked
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'), #checked
    path('request-change/', RequestEmailOrPhoneChangeView.as_view(), name='request-change'), #checked
    path('confirm-change/', ConfirmEmailOrPhoneChangeView.as_view(), name='confirm-change'), #checked
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('test-notification/', TestNotificationView.as_view(), name='test-notification'), # Test endpoint
    path('test-notification/self/', TestNotificationToSelfView.as_view(), name='test-notification-self'), # Quick test to self

]

