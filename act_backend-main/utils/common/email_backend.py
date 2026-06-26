"""
Custom email backend that handles SSL certificate verification issues in development.
"""
import ssl
import logging
from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class CustomSMTPEmailBackend(EmailBackend):
    """
    Custom SMTP email backend that handles SSL certificate verification.
    
    In development, can disable SSL verification if EMAIL_SSL_VERIFY is False.
    In production, always verifies SSL certificates.
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None, **kwargs):
        super().__init__(
            host=host, port=port, username=username, password=password,
            use_tls=use_tls, fail_silently=fail_silently, use_ssl=use_ssl,
            timeout=timeout, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile,
            **kwargs
        )
        
        # Check if SSL verification should be disabled (development only)
        self.ssl_verify = getattr(settings, 'EMAIL_SSL_VERIFY', True)
        
        # Log current settings
        logger.info(f"[EMAIL BACKEND] Initialized with EMAIL_SSL_VERIFY={self.ssl_verify}, DEBUG={settings.DEBUG}")
        
        # Only disable SSL verification in DEBUG mode for safety
        if not self.ssl_verify and not settings.DEBUG:
            logger.warning("[EMAIL BACKEND] EMAIL_SSL_VERIFY=False is ignored in production (DEBUG=False)")
            self.ssl_verify = True
        elif not self.ssl_verify and settings.DEBUG:
            logger.warning("[EMAIL BACKEND] ⚠️ SSL verification will be DISABLED (development mode)")
    
    def _get_ssl_context(self):
        """
        Override SSL context creation to handle certificate verification.
        This method is called by Django's SMTP backend before creating the connection.
        """
        if self.ssl_verify:
            # Use default SSL context (verifies certificates)
            context = ssl.create_default_context()
            logger.debug("[EMAIL] Using SSL certificate verification")
        else:
            # Create unverified SSL context (development only)
            context = ssl._create_unverified_context()
            logger.warning("[EMAIL] ⚠️ SSL certificate verification DISABLED (development mode)")
        
        return context
    
    def open(self):
        """
        Override open() to configure SSL context based on EMAIL_SSL_VERIFY setting.
        """
        if self.connection:
            return False
        
        try:
            # IMPORTANT: Set SSL context BEFORE calling parent's open()
            # Django's SMTP backend checks for self.ssl_context and uses it if it exists
            if self.ssl_verify:
                # Use default SSL context (verifies certificates)
                self.ssl_context = ssl.create_default_context()
                logger.info("[EMAIL BACKEND] Using SSL certificate verification")
            else:
                # Create unverified SSL context (development only)
                self.ssl_context = ssl._create_unverified_context()
                logger.warning("[EMAIL BACKEND] ⚠️ SSL certificate verification DISABLED (development mode)")
                logger.info(f"[EMAIL BACKEND] DEBUG={settings.DEBUG}, SSL_VERIFY={self.ssl_verify}")
            
            # Verify SSL context was set
            if not hasattr(self, 'ssl_context') or self.ssl_context is None:
                logger.error("[EMAIL BACKEND] ❌ SSL context was not set properly!")
                raise ValueError("SSL context not configured")
            
            logger.info(f"[EMAIL BACKEND] SSL context configured: verify_mode={self.ssl_context.verify_mode}")
            
            # Call parent's open() method which will use our ssl_context
            result = super().open()
            
            if result:
                logger.info("[EMAIL BACKEND] ✅ SMTP connection opened successfully")
            else:
                logger.warning("[EMAIL BACKEND] ⚠️ SMTP connection returned False")
            
            return result
            
        except Exception as e:
            logger.error(f"[EMAIL BACKEND] ❌ Failed to open SMTP connection: {e}")
            logger.error(f"[EMAIL BACKEND] Error type: {type(e).__name__}")
            if not self.fail_silently:
                raise
            return False

