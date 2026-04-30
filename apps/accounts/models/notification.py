from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    """
    Model to store notifications for users (passengers and drivers).
    Supports bilingual content (English and Arabic).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title_en = models.CharField(max_length=255)
    title_ar = models.CharField(max_length=255)
    desc_en = models.TextField()
    desc_ar = models.TextField()
    mobile_url = models.URLField(blank=True, null=True)
    web_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"Notification for {self.user.email} - {self.title_en}"


class FCMDevice(models.Model):
    """
    Model to store Firebase Cloud Messaging (FCM) device tokens.
    Each user can have multiple devices (e.g., phone, tablet).
    Device tokens are used to send push notifications.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'FCM Device'
        verbose_name_plural = 'FCM Devices'
        unique_together = ['user', 'device_token']

    def __str__(self):
        return f"Device for {self.user.email} - {self.device_token[:20]}..."

