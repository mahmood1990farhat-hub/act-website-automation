from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()


class OTP(models.Model):
    """
    Model to store OTP codes for password reset and other verification purposes.
    """
    PURPOSE_CHOICES = [
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_codes',
        help_text="User associated with this OTP"
    )
    code = models.CharField(
        max_length=6,
        help_text="6-digit OTP code"
    )
    email = models.EmailField(
        help_text="Email address where OTP was sent"
    )
    purpose = models.CharField(
        max_length=30,
        choices=PURPOSE_CHOICES,
        default='password_reset',
        help_text="Purpose of this OTP code"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the OTP was created"
    )
    expires_at = models.DateTimeField(
        help_text="When the OTP expires (15 minutes from creation)"
    )
    is_used = models.BooleanField(
        default=False,
        help_text="Whether this OTP has been used"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the OTP was used"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'code', 'purpose']),
            models.Index(fields=['expires_at', 'is_used']),
        ]
        verbose_name = 'OTP Code'
        verbose_name_plural = 'OTP Codes'
    
    def save(self, *args, **kwargs):
        """Set expiration time if not already set"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is valid (not expired and not used)"""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_as_used(self):
        """Mark OTP as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    def __str__(self):
        return f"OTP {self.code} for {self.email} ({self.purpose})"

