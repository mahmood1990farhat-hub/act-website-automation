import threading
import logging
from typing import List, Optional
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone as django_timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from utils.common.google_map import place_to_string  

logger = logging.getLogger(__name__)


# ---------- low-level helper ----------
def _send_mail_async(
    subject: str,
    message: str,
    recipient_list: List[str],
    html_message: Optional[str] = None,
    fail_silently: bool = True,
) -> None:
    """
    Send email asynchronously in a background thread with proper error handling
    """
    def _send_with_error_handling():
        print(f"[EMAIL] ⚠️ _send_with_error_handling thread started for: {', '.join(recipient_list)}")
        logger.info(f"[EMAIL] _send_with_error_handling thread started for: {', '.join(recipient_list)}")
        try:
            # Verify email settings are configured
            if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
                logger.error("[EMAIL] ❌ EMAIL_HOST_USER is not configured in settings")
                return
            
            if not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                logger.error("[EMAIL] ❌ EMAIL_HOST is not configured in settings")
                return
            
            if not hasattr(settings, 'EMAIL_HOST_PASSWORD') or not settings.EMAIL_HOST_PASSWORD:
                logger.error("[EMAIL] ❌ EMAIL_HOST_PASSWORD is not configured in settings")
                return
            
            print(f"[EMAIL] ⚠️ ✅ All email settings verified")
            logger.info(f"[EMAIL] ✅ All email settings verified")
            print(f"[EMAIL] ⚠️ Attempting to send email to: {', '.join(recipient_list)}")
            logger.info(f"[EMAIL] Attempting to send email to: {', '.join(recipient_list)}")
            logger.info(f"[EMAIL] Subject: {subject}")
            logger.info(f"[EMAIL] From: {settings.EMAIL_HOST_USER}")
            logger.info(f"[EMAIL] SMTP Host: {settings.EMAIL_HOST}:{getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
            
            # Use fail_silently=False to get actual error details
            try:
                print(f"[EMAIL] ⚠️ About to call send_mail()...")
                logger.info(f"[EMAIL] Calling Django send_mail()...")
                result = send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=recipient_list,
                    fail_silently=False,  # Changed to False to get actual errors
                    html_message=html_message,
                )
                
                print(f"[EMAIL] ⚠️ send_mail() returned: {result} (type: {type(result)})")
                logger.info(f"[EMAIL] send_mail() returned: {result}")
                
                if result:
                    print(f"[EMAIL] ✅✅✅ SUCCESS! Email accepted by SMTP server for: {', '.join(recipient_list)}")
                    print(f"[EMAIL] ⚠️ NOTE: If you don't receive the email, check:")
                    print(f"[EMAIL] ⚠️   1. Spam/Junk folder")
                    print(f"[EMAIL] ⚠️   2. Wait a few minutes (delivery delay)")
                    print(f"[EMAIL] ⚠️   3. Check email provider settings")
                    logger.info(f"[EMAIL] ✅ Successfully sent email to: {', '.join(recipient_list)}")
                    logger.info(f"[EMAIL] Note: Email was accepted by SMTP server. Check spam folder if not received.")
                else:
                    print(f"[EMAIL] ⚠️⚠️⚠️ Email sending returned False for: {', '.join(recipient_list)}")
                    logger.warning(f"[EMAIL] ⚠️ Email sending returned False for: {', '.join(recipient_list)}")
                    
            except Exception as smtp_error:
                # Now we'll get the actual SMTP error
                logger.error(f"[EMAIL] ❌ SMTP Error sending email to {', '.join(recipient_list)}")
                logger.error(f"[EMAIL] Error Type: {type(smtp_error).__name__}")
                logger.error(f"[EMAIL] Error Message: {str(smtp_error)}")
                
                # Log specific error details
                if hasattr(smtp_error, 'smtp_code'):
                    logger.error(f"[EMAIL] SMTP Code: {smtp_error.smtp_code}")
                if hasattr(smtp_error, 'smtp_error'):
                    logger.error(f"[EMAIL] SMTP Error: {smtp_error.smtp_error}")
                
                import traceback
                logger.error(f"[EMAIL] Full Traceback:\n{traceback.format_exc()}")
                
                # Common error messages with specific fixes
                error_str = str(smtp_error).lower()
                error_type = type(smtp_error).__name__
                
                if 'authentication' in error_str or '535' in error_str:
                    logger.error("[EMAIL] 💡 Possible fix: Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env file")
                elif 'connection' in error_str or 'timeout' in error_str:
                    logger.error("[EMAIL] 💡 Possible fix: Check EMAIL_HOST and EMAIL_PORT, verify firewall/network")
                elif 'tls' in error_str or 'ssl' in error_str or 'certificate' in error_str or 'SSLCertVerificationError' in error_type:
                    logger.error("[EMAIL] 💡 SSL Certificate Verification Error detected!")
                    logger.error("[EMAIL] 💡 For DEVELOPMENT: Add EMAIL_SSL_VERIFY=False to .env file")
                    logger.error("[EMAIL] 💡 For PRODUCTION: Install/update SSL certificates or contact your email provider")
                    logger.error("[EMAIL] 💡 Note: EMAIL_SSL_VERIFY=False only works when DEBUG=True")
                
        except Exception as e:
            logger.error(f"[EMAIL] ❌ Unexpected error in email sending: {str(e)}")
            logger.error(f"[EMAIL] Error details: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")
    
    # Start background thread for email sending
    thread = threading.Thread(
        target=_send_with_error_handling,
        daemon=True,
    )
    thread.start()
    logger.info(f"[EMAIL] Background thread started for email to {', '.join(recipient_list)}")


# ========== PASSENGER EMAILS ==========

def send_passenger_registration_confirmation(user) -> None:
    """
    Send welcome email to newly registered passenger
    """
    try:
        subject = _("Welcome to Airport & City Transfer!")
        message = _(
            "Hello %(first_name)s,\n\n"
            "Thank you for registering with Airport & City Transfer!\n\n"
            "Your account has been successfully created. You can now book trips and enjoy our services.\n\n"
            "If you have any questions, please don't hesitate to contact us.\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "first_name": user.first_name or user.get_full_name() or "Valued Customer",
        }
        _send_mail_async(subject, message, [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send passenger registration email to {user.email}: {str(e)}")


def send_passenger_confirmation(user, trip) -> None:
    """
    Send trip confirmation email to passenger
    """
    logger.info(f"[EMAIL] send_trip_accepted_to_passenger trip #{trip.id}, user {user.id}")
    try:
        if not user.email:
            logger.warning(f"[EMAIL] Cannot send trip accepted email: user {user.id} has no email")
            return
        pickup, dropoff = _trip_locations_for_email(trip)
        subject = _("Your Booking Confirmation – Airport & City Transfer")
        first_name = user.first_name or user.get_full_name() or "Valued Customer"
        map_url = (
            "https://www.google.com/maps/dir/?api=1"
            f"&origin={quote(pickup)}"
            f"&destination={quote(dropoff)}"
        )

        car_type = getattr(trip, "car_type", None)
        if car_type is not None:
            vehicle_label = car_type.name_en or car_type.name_ar or "Private Transfer"
        else:
            vehicle_label = "Private Transfer"

        context = {
            "first_name": first_name,
            "trip_id": trip.id,
            "origin": pickup,
            "destination": dropoff,
            "date": trip.trip_date.strftime("%d %B %Y"),
            "time": trip.trip_time.strftime("%I:%M %p").lstrip("0").lower(),
            "cost": f"{trip.cost:.2f}",
            "passenger_count": getattr(trip, "passengers_count", None) or "N/A",
            "vehicle_type": vehicle_label,
            "support_phone_primary": "+44 7464 940000",
            "support_phone_secondary": "+44 20 8153 0303",
            "support_email": "Info@airportandcitytransfer.com",
            "map_url": map_url,
            "header_image_url": _email_asset_url("trip_accepted/header-booking-confirmation.jpg"),
            # No map image file currently exists in static assets; template falls back to text link.
            "map_image_url": "",
            "footer_logo_image_url": _email_asset_url("trip_accepted/footer-logo.png"),
            "charity_image_url": _email_asset_url("trip_accepted/charity-cta.jpg"),
            "manage_booking_image_url": _email_asset_url("trip_accepted/manage-booking.png"),
            "facebook_icon_url": _email_asset_url("trip_accepted/facebook.png"),
            "instagram_icon_url": _email_asset_url("trip_accepted/instgram.png"),
            "x_icon_url": _email_asset_url("trip_accepted/x.png"),
            "youtube_icon_url": _email_asset_url("trip_accepted/youtube.png"),
            "blogger_icon_url": _email_asset_url("trip_accepted/b.png"),
            "tiktok_icon_url": _email_asset_url("trip_accepted/tiktok.png"),
            "google_play_badge_url": _email_asset_url("trip_accepted/google-play.png"),
            "app_store_badge_url": _email_asset_url("trip_accepted/apple.png"),
        }
        html_message = render_to_string("emails/trip_accepted_passenger.html", context)
        message = strip_tags(html_message)
        _send_mail_async(
            subject,
            message,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"[EMAIL] send_trip_accepted_to_passenger failed for trip #{trip.id}: {e}")



# ========== DRIVER ONBOARDING EMAILS ==========

def send_driver_onboarding_submitted(onboarding_request) -> None:
    """
    Send confirmation email when driver submits onboarding request (Step 1)
    """
    try:
        subject = _("Driver Onboarding Request Received")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Thank you for your interest in joining Airport & City Transfer as a driver.\n\n"
            "We have received your onboarding request and will review it shortly. You will receive an email "
            "notification once our team has reviewed your application.\n\n"
            "Request ID: #%(request_id)s\n"
            "Status: Pending Review\n\n"
            "We appreciate your patience.\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
            "request_id": onboarding_request.id,
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send onboarding submitted email to {onboarding_request.email_address}: {str(e)}")


def send_driver_step1_approval(onboarding_request) -> None:
    """
    Send email when driver's Step 1 (questionnaire) is approved
    """
    try:
        subject = _("Driver Onboarding - Step 1 Approved")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Congratulations! Your initial driver application has been approved.\n\n"
            "You can now log in to your account and proceed to upload your documents.\n\n"
            "Please visit our website or app to complete the document upload process.\n\n"
            "Your login credentials:\n"
            "- Email: %(email)s\n"
            "- Username: %(username)s\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
            "email": onboarding_request.email_address,
            "username": onboarding_request.user.username if onboarding_request.user else "N/A",
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send step 1 approval email to {onboarding_request.email_address}: {str(e)}")


def send_driver_step1_rejection(onboarding_request, reason: str = "") -> None:
    """
    Send email when driver's Step 1 (questionnaire) is rejected
    """
    try:
        subject = _("Driver Onboarding - Application Update")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Thank you for your interest in joining ATG as a driver.\n\n"
            "After careful review, we regret to inform you that your initial application has not been "
            "approved at this time.\n\n"
            "%(reason_section)s\n"
            "You may reapply in the future if your circumstances change.\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
            "reason_section": f"Reason: {reason}\n\n" if reason else "",
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send step 1 rejection email to {onboarding_request.email_address}: {str(e)}")


def send_driver_final_approval(onboarding_request) -> None:
    """
    Send email when driver's final approval is granted
    """
    try:
        subject = _("Driver Onboarding - Final Approval")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Congratulations! Your driver onboarding process has been completed successfully.\n\n"
            "You are now an approved driver and can start accepting rides.\n\n"
            "Welcome to the ATG team!\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send final approval email to {onboarding_request.email_address}: {str(e)}")


def send_driver_final_rejection(onboarding_request, reason: str = "") -> None:
    """
    Send email when driver's final application is rejected
    """
    try:
        subject = _("Driver Onboarding - Final Decision")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Thank you for completing the driver onboarding process.\n\n"
            "After careful review of your documents and application, we regret to inform you that "
            "your application has not been approved at this time.\n\n"
            "%(reason_section)s"
            "We appreciate your interest in joining ATG.\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
            "reason_section": f"Reason: {reason}\n\n" if reason else "",
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send final rejection email to {onboarding_request.email_address}: {str(e)}")


def send_driver_modification_request(onboarding_request, reason: str = "", files_to_modify: list = None) -> None:
    """
    Send email when driver's documents need modification
    """
    try:
        files_to_modify = files_to_modify or []
        
        # Map file names to user-friendly labels
        file_labels = {
            'pco': 'PCO License',
            'dbs': 'DBS Certificate',
            'dvla': 'DVLA License',
            'mot': 'MOT Certificate',
            'phv': 'PHV License'
        }
        
        files_list = ', '.join([file_labels.get(f, f.upper()) for f in files_to_modify]) if files_to_modify else 'documents'
        
        subject = _("Driver Onboarding - Documents Need Modification")
        message = _(
            "Dear %(full_name)s,\n\n"
            "Thank you for submitting your documents for review.\n\n"
            "After reviewing your uploaded documents, we need you to make some modifications before "
            "we can proceed with final approval.\n\n"
            "%(reason_section)s"
            "Please update the following document(s): %(files_list)s\n\n"
            "Please log in to your account and upload the updated documents. After uploading, "
            "you will need to confirm the upload to submit for review.\n\n"
            "If you have any questions, please don't hesitate to contact us.\n\n"
            "Best regards,\n"
            "The ATG Team"
        ) % {
            "full_name": onboarding_request.full_name,
            "reason_section": f"Required modifications:\n{reason}\n\n" if reason else "",
            "files_list": files_list,
        }
        _send_mail_async(subject, message, [onboarding_request.email_address], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send modification request email to {onboarding_request.email_address}: {str(e)}")


# ========== ADMIN NOTIFICATION EMAILS ==========

def _format_trip_luggage_label(trip) -> str:
    large = getattr(trip, "large_suitcase", 0) or 0
    small = getattr(trip, "small_suitcase", 0) or 0
    parts = []
    if large:
        parts.append(f"{large} Large")
    if small:
        parts.append(f"{small} Small")
    return ", ".join(parts) if parts else "None"


def send_internal_notification(trip) -> None:
    """
    Send internal notification to admin when a new trip is booked
    """
    logger.info(f"[EMAIL] send_internal_notification called for trip #{trip.id}")
    try:
        logger.info(f"[EMAIL] Building admin notification message for trip #{trip.id}")
        pickup, dropoff = _trip_locations_for_email(trip)
        passenger_user = trip.passenger.user if trip.passenger else None
        admin_email = getattr(settings, "ADMIN_EMAIL", "info@airportandcitytransfer.com")

        booking_ref = f"ACT-{trip.id}"
        booking_date = django_timezone.localtime(trip.created_at).strftime("%d %B %Y")
        payment_status = "Paid" if trip.is_paid else "Unpaid"
        amount_paid = f"£{trip.cost:.2f}"
        customer_name = (
            passenger_user.get_full_name() if passenger_user else "N/A"
        ) or "N/A"
        customer_phone = (
            (getattr(passenger_user, "phone_number", "") or "—")
            if passenger_user
            else "—"
        )
        customer_email = passenger_user.email if passenger_user else ""

        journey_date = trip.trip_date.strftime("%d %B %Y")
        journey_time = trip.trip_time.strftime("%I:%M %p").lstrip("0").lower()

        car_type = getattr(trip, "car_type", None)
        if car_type is not None:
            vehicle_label = car_type.name_en or car_type.name_ar or "Private transfer"
        else:
            vehicle_label = "Private transfer"

        if trip.stripe_payment_intent:
            payment_method = "Stripe (Card)"
            transaction_id = trip.stripe_payment_intent
        else:
            payment_method = "—"
            transaction_id = "—"

        subject = f"New Booking Received – {booking_ref}"
        context = {
            "booking_ref": booking_ref,
            "booking_date": booking_date,
            "payment_status": payment_status,
            "amount_paid": amount_paid,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "pickup": pickup,
            "dropoff": dropoff,
            "journey_date": journey_date,
            "journey_time": journey_time,
            "passengers_count": trip.passengers_count,
            "luggage_label": _format_trip_luggage_label(trip),
            "vehicle_label": vehicle_label,
            "payment_method": payment_method,
            "transaction_id": transaction_id,
            "footer_logo_url": _email_asset_url("trip_accepted/footer-logo.png"),
        }
        html_message = render_to_string("emails/admin_booking_notification.html", context)
        message = (
            f"A new booking has been received via the website.\n\n"
            f"Booking details\n"
            f"Booking number: {booking_ref}\n"
            f"Booking date: {booking_date}\n"
            f"Status: {payment_status}\n"
            f"Amount paid: {amount_paid}\n\n"
            f"Customer details\n"
            f"Name: {customer_name}\n"
            f"Phone: {customer_phone}\n"
            f"Email: {customer_email or '—'}\n\n"
            f"Journey details\n"
            f"Pick-up location: {pickup}\n"
            f"Drop-off location: {dropoff}\n"
            f"Date: {journey_date}\n"
            f"Time: {journey_time}\n"
            f"Passengers: {trip.passengers_count}\n"
            f"Luggage: {_format_trip_luggage_label(trip)}\n\n"
            f"Vehicle requirement\n"
            f"{vehicle_label}\n\n"
            f"Payment details\n"
            f"Payment status: {payment_status}\n"
            f"Amount paid: {amount_paid}\n"
            f"Payment method: {payment_method}\n"
            f"Transaction ID: {transaction_id}\n\n"
            f"Airport & City Transfer system\n"
        )

        logger.info(f"[EMAIL] Preparing admin notification email for trip #{trip.id} to {admin_email}")
        logger.info(f"[EMAIL] Calling _send_mail_async for admin notification")
        _send_mail_async(
            subject,
            message,
            [admin_email],
            html_message=html_message,
            fail_silently=True,
        )
        logger.info(f"[EMAIL] _send_mail_async called (running in background thread)")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to prepare admin notification email for trip #{trip.id}: {str(e)}")
        import traceback
        logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")


def _trip_locations_for_email(trip):
    pickup = (
        place_to_string(trip.pickup_place_id)
        or trip.pickup_str
        or f"{trip.pickup_lat},{trip.pickup_lng}"
    )
    dropoff = (
        place_to_string(trip.dropoff_place_id)
        or trip.dropoff_str
        or f"{trip.dropoff_lat},{trip.dropoff_lng}"
    )
    return pickup, dropoff


def _email_asset_url(path: str) -> str:
    """
    Build a public absolute URL for email assets (images/icons/badges).
    """
    base = getattr(settings, "ACT_EMAIL_ASSETS_BASE_URL", "").rstrip("/")
    clean_path = (path or "").lstrip("/")
    if not base or not clean_path:
        return ""
    return f"{base}/{clean_path}"


def send_trip_accepted_to_passenger(
    user,
    trip,
    driver_user=None,
    is_guest_driver: bool = False,
    guest_driver_info: Optional[dict] = None,
) -> None:
    """
    Email to passenger when a driver accepts / confirms the trip.
    """
    logger.info(f"[EMAIL] send_trip_accepted_to_passenger trip #{trip.id}, user {user.id}")
    try:
        if not user.email:
            logger.warning(f"[EMAIL] Cannot send trip accepted email: user {user.id} has no email")
            return

        first_name = user.first_name or user.get_full_name() or "Valued Customer"

        if is_guest_driver and guest_driver_info:
            driver_name = guest_driver_info.get("name") or "External Driver"
            driver_phone = guest_driver_info.get("phone") or "N/A"
            guest_car = guest_driver_info.get("car") or {}
            vehicle_label = (
                guest_car.get("brand_model")
                or guest_car.get("brand")
                or "Private Transfer"
            )
            registration_number = guest_car.get("registration_number") or "N/A"
            vehicle_color = guest_car.get("color") or "N/A"
        else:
            driver_name = (
                driver_user.get_full_name().strip()
                if driver_user and driver_user.get_full_name().strip()
                else (driver_user.first_name if driver_user else "")
            ) or "N/A"
            driver_phone = getattr(driver_user, "phone_number", "") or "N/A"

            vehicle = (
                trip.base_driver.normal_driver.vehicle
                if getattr(trip, "base_driver", None)
                and hasattr(trip.base_driver, "normal_driver")
                and trip.base_driver.normal_driver
                else None
            )
            vehicle_type = getattr(vehicle, "vehicle_type", None)
            vehicle_label = (
                getattr(vehicle_type, "name_en", None)
                or getattr(vehicle_type, "name_ar", None)
                or "Private Transfer"
            )
            registration_number = getattr(vehicle, "vehicle_number", "") or "N/A"
            vehicle_color = "N/A"

        context = {
            "first_name": first_name,
            "driver_name": driver_name,
            "driver_phone": driver_phone,
            "vehicle_name": vehicle_label,
            "vehicle_registration": registration_number,
            "vehicle_color": vehicle_color,
            "support_phone_primary": "+44 7464 940000",
            "support_phone_secondary": "+44 20 8153 0303",
            "support_email": "info@airportandcitytransfer.com",
            "support_website": "https://airportandcitytransfer.com/en",
            "footer_logo_image_url": _email_asset_url("trip_accepted/footer-logo.png"),
        }
        subject = _("Your Driver Details – Airport & City Transfer")
        html_message = render_to_string("emails/trip_driver_details_passenger.html", context)
        message = strip_tags(html_message)
        _send_mail_async(
            subject,
            message,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"[EMAIL] send_trip_accepted_to_passenger failed for trip #{trip.id}: {e}")

def send_trip_accepted_to_admin(trip, driver_user) -> None:
    """
    Email to operations admin when a driver accepts a trip.
    """
    logger.info(f"[EMAIL] send_trip_accepted_to_admin trip #{trip.id}")
    try:
        pickup, dropoff = _trip_locations_for_email(trip)
        passenger_user = trip.passenger.user if trip.passenger else None
        admin_email = getattr(settings, "ADMIN_EMAIL", "info@airportandcitytransfer.com")
        driver_label = (
            f"{driver_user.get_full_name()} ({driver_user.email})"
            if driver_user
            else "N/A"
        )
        subject = f"Trip confirmed by driver – #{trip.id}"
        message = (
            f"A driver has accepted this trip:\n\n"
            f"Trip ID: #{trip.id}\n"
            f"Passenger: {passenger_user.get_full_name() if passenger_user else 'N/A'} "
            f"({passenger_user.email if passenger_user else 'N/A'})\n"
            f"Driver: {driver_label}\n"
            f"Pickup: {pickup}\n"
            f"Drop-off: {dropoff}\n"
            f"Date: {trip.trip_date} {trip.trip_time}\n"
            f"Amount: £{trip.cost:.2f}\n"
        )
        _send_mail_async(subject, message, [admin_email], fail_silently=True)
    except Exception as e:
        logger.error(f"[EMAIL] send_trip_accepted_to_admin failed for trip #{trip.id}: {e}")


def send_passenger_trip_cancellation_to_passenger(user, trip, refund_message: str = "") -> None:
    """
    Email to passenger when they cancel their own trip (full cancellation, not driver reassign flow).
    """
    logger.info(f"[EMAIL] send_passenger_trip_cancellation_to_passenger trip #{trip.id}")
    try:
        if not user.email:
            logger.warning(f"[EMAIL] Cannot send passenger cancel email: user {user.id} has no email")
            return
        pickup, dropoff = _trip_locations_for_email(trip)
        subject = _("Trip cancelled – #{}").format(trip.id)
        first_name = user.first_name or user.get_full_name() or "Valued Customer"
        car_type = getattr(trip, "car_type", None)
        if car_type is not None:
            vehicle_label = car_type.name_en or car_type.name_ar or "Private Transfer"
        else:
            vehicle_label = "Private Transfer"
        context = {
            "first_name": first_name,
            "refund_message": refund_message,
            "website_url": "https://airportandcitytransfer.com/en",
            "trip_id": trip.id,
            "passenger_name": first_name,
            "passenger_count": getattr(trip, "passengers_count", None) or "N/A",
            "vehicle_type": vehicle_label,
            "cost": f"{trip.cost:.2f}",
            "origin": pickup,
            "destination": dropoff,
            "date": trip.trip_date.strftime("%d %B %Y"),
            "time": trip.trip_time.strftime("%I:%M %p").lstrip("0").lower(),
            "cancellation_image_url": _email_asset_url("trip_cancel/cancellation.png"),
            "charity_image_url": _email_asset_url("trip_cancel/charity.png"),
        }
        html_message = render_to_string("emails/trip_cancelled_passenger.html", context)
        message = _(
            "Hello %(first_name)s,\n\n"
            "Your booking with Airport & City Transfer has been successfully cancelled.\n\n"
            "%(refund_message_text)s"
            "If you would like to arrange a new journey, visit:\n"
            "%(website_url)s\n\n"
            "Yours sincerely,\n"
            "Airport & City Transfer Team"
        ) % {
            "first_name": first_name,
            "refund_message_text": f"{refund_message}\n\n" if refund_message else "",
            "website_url": "https://airportandcitytransfer.com/en",
        }
        _send_mail_async(
            subject,
            message,
            [user.email],
            html_message=html_message,
            fail_silently=True,
        )
    except Exception as e:
        logger.error(f"[EMAIL] send_passenger_trip_cancellation_to_passenger failed trip #{trip.id}: {e}")


def send_passenger_trip_cancellation_to_admin(trip, refund_message: str = "") -> None:
    """
    Email to admin when a passenger cancels a trip (pending cancel or policy-based cancel).
    """
    logger.info(f"[EMAIL] send_passenger_trip_cancellation_to_admin trip #{trip.id}")
    try:
        pickup, dropoff = _trip_locations_for_email(trip)
        passenger_user = trip.passenger.user if trip.passenger else None
        admin_email = getattr(settings, "ADMIN_EMAIL", "info@airportandcitytransfer.com")
        subject = f"Passenger cancelled trip – #{trip.id}"
        message = (
            f"The passenger cancelled this trip:\n\n"
            f"Trip ID: #{trip.id}\n"
            f"Passenger: {passenger_user.get_full_name() if passenger_user else 'N/A'} "
            f"({passenger_user.email if passenger_user else 'N/A'})\n"
            f"Pickup: {pickup}\n"
            f"Drop-off: {dropoff}\n"
            f"Date: {trip.trip_date} {trip.trip_time}\n"
            f"Amount: £{trip.cost:.2f}\n"
            f"Status after cancel: {trip.status}\n"
        )
        if refund_message:
            message += f"Refund / payment note: {refund_message}\n"
        _send_mail_async(subject, message, [admin_email], fail_silently=True)
    except Exception as e:
        logger.error(f"[EMAIL] send_passenger_trip_cancellation_to_admin failed trip #{trip.id}: {e}")


def send_admin_onboarding_notification(onboarding_request) -> None:
    """
    Send notification to admin when a new driver onboarding request is submitted
    """
    try:
        subject = f"New Driver Onboarding Request – #{onboarding_request.id}"
        message = (
            f"A new driver onboarding request has been submitted:\n\n"
            f"Request ID: #{onboarding_request.id}\n"
            f"Driver Name: {onboarding_request.full_name}\n"
            f"Email: {onboarding_request.email_address}\n"
            f"Mobile: {onboarding_request.mobile_number}\n"
            f"Status: {onboarding_request.get_status_display()}\n"
            f"Submitted: {onboarding_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Please review the request in the admin panel.\n"
        )
        _send_mail_async(subject, message, ["info@airportandcitytransfer.com"], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send admin onboarding notification email: {str(e)}")


# ========== DRIVER CANCELLATION AND REASSIGNMENT EMAILS ==========

def send_driver_cancellation_to_passenger(user, trip) -> None:
    """
    Send email to passenger when driver cancels their trip
    """
    logger.info(f"[EMAIL] send_driver_cancellation_to_passenger called for trip #{trip.id}, user {user.id}")
    try:
        if not user.email:
            logger.warning(f"[EMAIL] Cannot send driver cancellation email: user {user.id} has no email address")
            return
        
        pickup = (
            place_to_string(trip.pickup_place_id)
            or trip.pickup_str
            or f"{trip.pickup_lat},{trip.pickup_lng}"
        )

        dropoff = (
            place_to_string(trip.dropoff_place_id)
            or trip.dropoff_str
            or f"{trip.dropoff_lat},{trip.dropoff_lng}"
        )

        subject = _("Driver Cancelled Your Trip – #{}").format(trip.id)
        message = _(
            "Hello %(first_name)s\n\n"
            "We regret to inform you that the driver assigned to your trip has cancelled.\n\n"
            "Trip Details:\n"
            "Trip ID: #%(trip_id)s\n"
            "From: %(origin)s\n"
            "To: %(destination)s\n"
            "Date: %(date)s at %(time)s\n"
            "Cost: £%(cost).2f\n\n"
            "Our team will connect you with another driver shortly. We apologize for any inconvenience.\n\n"
            "Thank you for your patience."
        ) % {
            "first_name": user.first_name or user.get_full_name() or "Valued Customer",
            "trip_id": trip.id,
            "origin": pickup,
            "destination": dropoff,
            "date": trip.trip_date.strftime("%d %b %Y"),
            "time": trip.trip_time.strftime("%H:%M"),
            "cost": trip.cost,
        }
        
        logger.info(f"[EMAIL] Preparing driver cancellation email for trip #{trip.id} to {user.email}")
        _send_mail_async(subject, message, [user.email], fail_silently=True)
        logger.info(f"[EMAIL] Driver cancellation email sent to passenger {user.email}")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send driver cancellation email for trip #{trip.id} to {user.email}: {str(e)}")
        import traceback
        logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")


def send_driver_cancellation_to_admin(trip) -> None:
    """
    Send email to admin when a driver cancels a trip
    """
    logger.info(f"[EMAIL] send_driver_cancellation_to_admin called for trip #{trip.id}")
    try:
        pickup = (
            place_to_string(trip.pickup_place_id)
            or trip.pickup_str
            or f"{trip.pickup_lat},{trip.pickup_lng}"
        )

        dropoff = (
            place_to_string(trip.dropoff_place_id)
            or trip.dropoff_str
            or f"{trip.dropoff_lat},{trip.dropoff_lng}"
        )

        passenger_user = trip.passenger.user if trip.passenger else None
        driver_user = trip.base_driver.user if trip.base_driver else None
        
        admin_email = getattr(settings, 'ADMIN_EMAIL', 'info@airportandcitytransfer.com')
        
        subject = f"Driver Cancelled Trip – #{trip.id}"
        message = (
            f"A driver has cancelled a trip:\n\n"
            f"Trip ID: #{trip.id}\n"
            f"Passenger: {passenger_user.get_full_name() if passenger_user else 'N/A'} ({passenger_user.email if passenger_user else 'N/A'})\n"
            f"Driver: {driver_user.get_full_name() if driver_user else 'N/A'} ({driver_user.email if driver_user else 'N/A'})\n"
            f"Pickup: {pickup}\n"
            f"Drop-off: {dropoff}\n"
            f"Date: {trip.trip_date} {trip.trip_time}\n"
            f"Amount: £{trip.cost:.2f}\n"
        )
        
        if trip.cancellation_reason:
            message += f"Cancellation Reason: {trip.cancellation_reason}\n"
        
        if trip.cancelled_at:
            message += f"Cancelled At: {trip.cancelled_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        message += "\nPlease reassign this trip to another driver from the admin panel.\n"
        
        logger.info(f"[EMAIL] Preparing driver cancellation notification email for trip #{trip.id} to {admin_email}")
        _send_mail_async(subject, message, [admin_email], fail_silently=True)
        logger.info(f"[EMAIL] Driver cancellation notification email sent to admin")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send driver cancellation notification email for trip #{trip.id}: {str(e)}")
        import traceback
        logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")


def send_trip_reassigned_to_passenger(user, trip, is_guest_driver=False, guest_driver_info=None) -> None:
    """
    Send email to passenger when trip is reassigned to a new driver (system or guest)
    
    Args:
        user: Passenger user object
        trip: Trip object
        is_guest_driver: True if assigned to guest/external driver
        guest_driver_info: Dict with 'name', 'phone', 'company' (optional) if is_guest_driver is True
    """
    logger.info(f"[EMAIL] send_trip_reassigned_to_passenger called for trip #{trip.id}, user {user.id}, is_guest_driver={is_guest_driver}")
    try:
        if not user.email:
            logger.warning(f"[EMAIL] Cannot send trip reassignment email: user {user.id} has no email address")
            return
        
        pickup = (
            place_to_string(trip.pickup_place_id)
            or trip.pickup_str
            or f"{trip.pickup_lat},{trip.pickup_lng}"
        )

        dropoff = (
            place_to_string(trip.dropoff_place_id)
            or trip.dropoff_str
            or f"{trip.dropoff_lat},{trip.dropoff_lng}"
        )

        if is_guest_driver and guest_driver_info:
            # Guest driver assignment
            driver_name = guest_driver_info.get('name', 'External Driver')
            driver_phone = guest_driver_info.get('phone', 'N/A')
            driver_company = guest_driver_info.get('company', '')
            
            subject = _("External Driver Assigned to Your Trip – #{}").format(trip.id)
            message = _(
                "Hello %(first_name)s\n\n"
                "Your trip has been assigned to an external driver.\n\n"
                "Trip Details:\n"
                "Trip ID: #%(trip_id)s\n"
                "From: %(origin)s\n"
                "To: %(destination)s\n"
                "Date: %(date)s at %(time)s\n"
                "Cost: £%(cost).2f\n\n"
                "Driver Information:\n"
                "Name: %(driver_name)s\n"
                "Phone: %(driver_phone)s\n"
            ) % {
                "first_name": user.first_name or user.get_full_name() or "Valued Customer",
                "trip_id": trip.id,
                "origin": pickup,
                "destination": dropoff,
                "date": trip.trip_date.strftime("%d %b %Y"),
                "time": trip.trip_time.strftime("%H:%M"),
                "cost": trip.cost,
                "driver_name": driver_name,
                "driver_phone": driver_phone,
            }
            
            if driver_company:
                message += _("Company: %s\n") % driver_company
            
            message += _("\nPlease contact the driver directly using the phone number provided.\n\nThank you!")
        else:
            # System driver reassignment
            driver_user = trip.base_driver.user if trip.base_driver and trip.base_driver.user else None
            driver_name = driver_user.get_full_name() if driver_user else "Assigned Driver"
            driver_phone = driver_user.phone_number if driver_user else "N/A"
            
            subject = _("Trip Reassigned – #{}").format(trip.id)
            message = _(
                "Hello %(first_name)s\n\n"
                "Your trip has been reassigned to a new driver.\n\n"
                "Trip Details:\n"
                "Trip ID: #%(trip_id)s\n"
                "From: %(origin)s\n"
                "To: %(destination)s\n"
                "Date: %(date)s at %(time)s\n"
                "Cost: £%(cost).2f\n\n"
                "Driver Information:\n"
                "Name: %(driver_name)s\n"
                "Phone: %(driver_phone)s\n\n"
                "The driver will contact you shortly.\n\n"
                "Thank you for your patience."
            ) % {
                "first_name": user.first_name or user.get_full_name() or "Valued Customer",
                "trip_id": trip.id,
                "origin": pickup,
                "destination": dropoff,
                "date": trip.trip_date.strftime("%d %b %Y"),
                "time": trip.trip_time.strftime("%H:%M"),
                "cost": trip.cost,
                "driver_name": driver_name,
                "driver_phone": driver_phone,
            }
        
        logger.info(f"[EMAIL] Preparing trip reassignment email for trip #{trip.id} to {user.email}")
        _send_mail_async(subject, message, [user.email], fail_silently=True)
        logger.info(f"[EMAIL] Trip reassignment email sent to passenger {user.email}")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send trip reassignment email for trip #{trip.id} to {user.email}: {str(e)}")


def send_password_reset_otp(user, otp_code) -> None:
    """
    Send password reset OTP code via email to user.
    Supports bilingual (English/Arabic) email content.
    
    Args:
        user: CustomUser instance
        otp_code: 6-digit OTP code
    """
    if not user or not user.email:
        logger.warning(f"[EMAIL] Cannot send password reset OTP: user {user.id if user else 'None'} has no email address")
        return
    
    try:
        # English email content
        subject_en = "Password Reset OTP Code"
        message_en = f"""
Hello {user.first_name or 'User'},

You have requested to reset your password. Please use the following OTP code to complete the process:

OTP Code: {otp_code}

This code will expire in 15 minutes.

If you did not request this password reset, please ignore this email.

Best regards,
Airport & City Transfer Team
"""
        
        # Arabic email content
        subject_ar = "رمز إعادة تعيين كلمة المرور"
        message_ar = f"""
مرحباً {user.first_name or 'المستخدم'},

لقد طلبت إعادة تعيين كلمة المرور. يرجى استخدام رمز OTP التالي لإكمال العملية:

رمز OTP: {otp_code}

سينتهي صلاحية هذا الرمز خلال 15 دقيقة.

إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذا البريد الإلكتروني.

مع أطيب التحيات،
فريق نقل المطار والمدينة
"""
        
        # Send email (use English by default, but both are prepared)
        # In a real implementation, you might want to detect user's preferred language
        _send_mail_async(
            subject=subject_en,
            message=message_en,
            recipient_list=[user.email],
            html_message=None,
            fail_silently=True
        )
        
        logger.info(f"[EMAIL] Password reset OTP sent to {user.email}")
        
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send password reset OTP to {user.email}: {str(e)}")
        import traceback
        logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")       
        logger.error(f"[EMAIL] Traceback: {traceback.format_exc()}")
