import random
import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import OTP

logger = logging.getLogger(__name__)
User = get_user_model()


def generate_otp_code():
    """Generate a random 6-digit OTP code"""
    return str(random.randint(100000, 999999))


def send_otp_email(user, code, purpose='password_reset'):
    """
    Send OTP code via email using existing email infrastructure.
    
    Args:
        user: User instance
        code: 6-digit OTP code
        purpose: Purpose of the OTP (default: 'password_reset')
    """
    try:
        from utils.common.email import send_password_reset_otp
        send_password_reset_otp(user, code)
        logger.info(f"OTP email sent to {user.email} for purpose: {purpose}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
        return False


def create_otp_for_user(user, purpose='password_reset'):
    """
    Create and save OTP record for a user.
    
    Args:
        user: User instance
        purpose: Purpose of the OTP (default: 'password_reset')
    
    Returns:
        OTP instance
    """
    # Invalidate any existing unused OTPs for this user and purpose
    OTP.objects.filter(
        user=user,
        email=user.email,
        purpose=purpose,
        is_used=False
    ).update(is_used=True, used_at=timezone.now())
    
    # Generate new OTP code
    code = generate_otp_code()
    
    # Create OTP record
    otp = OTP.objects.create(
        user=user,
        code=code,
        email=user.email,
        purpose=purpose
    )
    
    logger.info(f"OTP created for user {user.id} ({user.email}): {code}")
    return otp


def verify_otp_code(email, code, purpose='password_reset'):
    """
    Verify OTP code and mark as used if valid.
    
    Args:
        email: User's email address
        code: OTP code to verify
        purpose: Purpose of the OTP (default: 'password_reset')
    
    Returns:
        tuple: (is_valid: bool, otp_instance: OTP or None, error_message: str or None)
    """
    try:
        # Normalize email to lowercase
        normalized_email = email.lower() if email else None
        
        if not normalized_email or not code:
            return False, None, "Email and OTP code are required"
        
        # Find the most recent valid OTP for this email and purpose
        otp = OTP.objects.filter(
            email__iexact=normalized_email,
            code=code,
            purpose=purpose,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return False, None, "Invalid OTP code"
        
        # Check if OTP is valid (not expired)
        if not otp.is_valid():
            return False, None, "OTP code has expired. Please request a new one."
        
        # Mark OTP as used
        otp.mark_as_used()
        
        logger.info(f"OTP verified successfully for {normalized_email}")
        return True, otp, None
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False, None, "An error occurred while verifying OTP code"

