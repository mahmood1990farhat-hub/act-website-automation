from .auht_views import LoginView, LogoutView, TokenRefreshView, DeleteAccountView
from .otp_send_views import SendOTPAPIView, VerifyOTPAPIView
from .notification_views import UserNotificationListView
from .edit_info import RequestEmailOrPhoneChangeView, ConfirmEmailOrPhoneChangeView
from .password_views import ForgetPasswordView, ResetPasswordView, ChangePasswordView
from .test_notification_views import TestNotificationView, TestNotificationToSelfView


