from firebase_admin import messaging
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

# Notification Types
NOTIFICATION_TYPE_NEW_TRIP_REQUEST = "NEW_TRIP_REQUEST"
NOTIFICATION_TYPE_TRIP_CREATED = "TRIP_CREATED"
NOTIFICATION_TYPE_TRIP_ACCEPTED = "TRIP_ACCEPTED"
NOTIFICATION_TYPE_DRIVER_ON_THE_WAY = "DRIVER_ON_THE_WAY"
NOTIFICATION_TYPE_TRIP_STARTED = "TRIP_STARTED"
NOTIFICATION_TYPE_TRIP_COMPLETED = "TRIP_COMPLETED"
NOTIFICATION_TYPE_TRIP_CANCELLED = "TRIP_CANCELLED"
NOTIFICATION_TYPE_DRIVER_CANCELLED = "DRIVER_CANCELLED"
NOTIFICATION_TYPE_TRIP_REASSIGNED = "TRIP_REASSIGNED"
NOTIFICATION_TYPE_GUEST_DRIVER_ASSIGNED = "GUEST_DRIVER_ASSIGNED"

def send_fcm_notification(device_token, title, body, data=None, user=None, notification_type=None, trip_id=None):
    """
    Send FCM notification to a device using the unified Firebase app.
    
    Args:
        device_token: FCM device token
        title: Notification title
        body: Notification body
        data: Additional data payload (dict)
        user: User instance (optional, kept for backward compatibility but no longer used for app selection)
        notification_type: Type of notification (e.g., "NEW_TRIP_REQUEST", "TRIP_COMPLETED")
        trip_id: Trip ID associated with the notification
    """
    try:
        # Build data payload with notification_type and trip_id
        fcm_data = data.copy() if data else {}
        if notification_type:
            fcm_data['notification_type'] = notification_type
        if trip_id:
            fcm_data['trip_id'] = str(trip_id)
        # Keep existing 'url' field for backward compatibility
        if 'url' not in fcm_data:
            fcm_data['url'] = ""
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device_token,
            data=fcm_data,
        )

        # Send using the default unified Firebase app
        response = messaging.send(message)
        
        logger.info(f"Notification sent successfully: {response}")
        return response
    except messaging.UnregisteredError:
        logger.warning(f"Device token is unregistered: {device_token[:20]}...")
        # Optionally delete the invalid token from database
        if user:
            from apps.accounts.models import FCMDevice
            FCMDevice.objects.filter(user=user, device_token=device_token).delete()
    except Exception as e:
        logger.error(f"An error occurred while sending notification: {e}")
        raise


def notify_user_sync(user, title_en, title_ar, desc_ar, desc_en, locale='en', mobile_url=None, web_url=None, notification_type=None, trip_id=None):
    """
    Synchronous version of notify_user_task.
    Sends notification immediately without Celery.
    Use this as a fallback when Celery/Redis is unavailable.
    
    Args:
        user: User ID or User instance
        title_en: Notification title in English
        title_ar: Notification title in Arabic
        desc_en: Notification description in English
        desc_ar: Notification description in Arabic
        locale: User's locale ('en' or 'ar')
        mobile_url: Optional mobile app deep link
        web_url: Optional web URL
        notification_type: Type of notification (e.g., "NEW_TRIP_REQUEST", "TRIP_COMPLETED")
        trip_id: Trip ID associated with the notification
    """
    from apps.accounts.models import FCMDevice, Notification
    from django.contrib.auth import get_user_model
    import traceback
    
    User = get_user_model()
    
    logger.info(f"[NOTIFICATION SYNC] Starting synchronous notification for user={user}, locale={locale}, title_en='{title_en}'")
    
    # Get user instance if passed as ID
    if isinstance(user, int):
        try:
            user = User.objects.get(id=user)
            logger.info(f"[NOTIFICATION SYNC] Found user: {user.id} ({user.email}), account_type={getattr(user, 'account_type', 'N/A')}")
        except User.DoesNotExist:
            logger.error(f"[NOTIFICATION SYNC] User with ID {user} does not exist")
            return
        except Exception as e:
            logger.error(f"[NOTIFICATION SYNC] Error fetching user {user}: {e}")
            logger.error(traceback.format_exc())
            return
    
    # Select title and description based on locale
    if locale == 'ar':
        title = title_ar
        desc = desc_ar
    else:
        title = title_en
        desc = desc_en

    logger.info(f"[NOTIFICATION SYNC] Selected title='{title}', desc='{desc[:50]}...'")

    # Get all devices for this user
    devices = FCMDevice.objects.filter(user=user)
    device_count = devices.count()
    logger.info(f"[NOTIFICATION SYNC] Found {device_count} device(s) for user {user.id}")
    
    if device_count == 0:
        logger.warning(f"[NOTIFICATION SYNC] No device tokens found for user {user.id}. User needs to login with device_token.")
        # Still create notification record in database even if no devices
    else:
        for device in devices:
            logger.info(f"[NOTIFICATION SYNC] Processing device {device.id}, token: {device.device_token[:30]}...")
    
    # Create notification record in database
    try:
        notification = Notification.objects.create(
            user=user,
            title_en=title_en,
            title_ar=title_ar,
            desc_en=desc_en,
            desc_ar=desc_ar,
            mobile_url=mobile_url,
            web_url=web_url
        )
        logger.info(f"[NOTIFICATION SYNC] Notification record created in database: ID={notification.id}")
    except Exception as e:
        logger.error(f"[NOTIFICATION SYNC] Failed to create notification record: {e}")
        logger.error(traceback.format_exc())
        return
    
    # Send notification to each device
    success_count = 0
    failure_count = 0
    
    for device in devices:
        try:
            logger.info(f"[NOTIFICATION SYNC] Sending FCM notification to device {device.id}...")
            response = send_fcm_notification(
                device_token=device.device_token,
                title=title,
                body=desc,
                data={"url": mobile_url or ""},
                user=user,
                notification_type=notification_type,
                trip_id=trip_id
            )
            logger.info(f"[NOTIFICATION SYNC] ✅ Successfully sent notification to device {device.id}. Firebase response: {response}")
            success_count += 1
        except Exception as e:
            logger.error(f"[NOTIFICATION SYNC] ❌ Failed to send notification to device {device.id}: {e}")
            logger.error(traceback.format_exc())
            failure_count += 1
            continue
    
    logger.info(f"[NOTIFICATION SYNC] Completed. Success: {success_count}, Failures: {failure_count}, Total devices: {device_count}")


@shared_task
def notify_user_task(user, title_en, title_ar, desc_ar, desc_en, locale='en', mobile_url=None, web_url=None, notification_type=None, trip_id=None):
    """
    Send notification to a user via FCM.
    Uses the unified Firebase app for all users.
    
    Args:
        user: User instance (CustomUser)
        title_en: Notification title in English
        title_ar: Notification title in Arabic
        desc_en: Notification description in English
        desc_ar: Notification description in Arabic
        locale: User's locale ('en' or 'ar')
        mobile_url: Optional mobile app deep link
        web_url: Optional web URL
        notification_type: Type of notification (e.g., "NEW_TRIP_REQUEST", "TRIP_COMPLETED")
        trip_id: Trip ID associated with the notification
    """
    from apps.accounts.models import FCMDevice, Notification
    from django.contrib.auth import get_user_model
    import traceback
    
    User = get_user_model()
    
    logger.info(f"[NOTIFICATION TASK] Starting notification task for user={user}, locale={locale}, title_en='{title_en}'")
    
    # Get user instance if passed as ID
    if isinstance(user, int):
        try:
            user = User.objects.get(id=user)
            logger.info(f"[NOTIFICATION TASK] Found user: {user.id} ({user.email}), account_type={getattr(user, 'account_type', 'N/A')}")
        except User.DoesNotExist:
            logger.error(f"[NOTIFICATION TASK] User with ID {user} does not exist")
            return
        except Exception as e:
            logger.error(f"[NOTIFICATION TASK] Error fetching user {user}: {e}")
            logger.error(traceback.format_exc())
            return
    
    # Select title and description based on locale
    if locale == 'ar':
        title = title_ar
        desc = desc_ar
    else:
        title = title_en
        desc = desc_en

    logger.info(f"[NOTIFICATION TASK] Selected title='{title}', desc='{desc[:50]}...'")

    # Get all devices for this user
    devices = FCMDevice.objects.filter(user=user)
    device_count = devices.count()
    logger.info(f"[NOTIFICATION TASK] Found {device_count} device(s) for user {user.id}")
    
    if device_count == 0:
        logger.warning(f"[NOTIFICATION TASK] No device tokens found for user {user.id}. User needs to login with device_token.")
        # Still create notification record in database even if no devices
    else:
        for device in devices:
            logger.info(f"[NOTIFICATION TASK] Processing device {device.id}, token: {device.device_token[:30]}...")
    
    # Create notification record in database
    try:
        notification = Notification.objects.create(
            user=user,
            title_en=title_en,
            title_ar=title_ar,
            desc_en=desc_en,
            desc_ar=desc_ar,
            mobile_url=mobile_url,
            web_url=web_url
        )
        logger.info(f"[NOTIFICATION TASK] Notification record created in database: ID={notification.id}")
    except Exception as e:
        logger.error(f"[NOTIFICATION TASK] Failed to create notification record: {e}")
        logger.error(traceback.format_exc())
        return
    
    # Send notification to each device using unified Firebase app
    success_count = 0
    failure_count = 0
    
    for device in devices:
        try:
            logger.info(f"[NOTIFICATION TASK] Sending FCM notification to device {device.id}...")
            response = send_fcm_notification(
                device_token=device.device_token,
                title=title,
                body=desc,
                data={"url": mobile_url or ""},
                user=user,  # Kept for backward compatibility
                notification_type=notification_type,
                trip_id=trip_id
            )
            logger.info(f"[NOTIFICATION TASK] ✅ Successfully sent notification to device {device.id}. Firebase response: {response}")
            success_count += 1
        except Exception as e:
            logger.error(f"[NOTIFICATION TASK] ❌ Failed to send notification to device {device.id}: {e}")
            logger.error(traceback.format_exc())
            failure_count += 1
            continue
    
    logger.info(f"[NOTIFICATION TASK] Completed. Success: {success_count}, Failures: {failure_count}, Total devices: {device_count}")


def notify_user(user, title_en, title_ar, desc_ar, desc_en, locale='en', mobile_url=None, web_url=None, use_async=True, notification_type=None, trip_id=None):
    """
    Smart notification sender that tries async (Celery) first, falls back to sync if Celery unavailable.
    
    Args:
        user: User ID or User instance
        title_en: Notification title in English
        title_ar: Notification title in Arabic
        desc_en: Notification description in English
        desc_ar: Notification description in Arabic
        locale: User's locale ('en' or 'ar')
        mobile_url: Optional mobile app deep link
        web_url: Optional web URL
        use_async: If True, try async first (default). If False, use sync directly.
        notification_type: Type of notification (e.g., "NEW_TRIP_REQUEST", "TRIP_COMPLETED")
        trip_id: Trip ID associated with the notification
    
    Returns:
        True if notification was queued/sent successfully, False otherwise
    """
    from django.conf import settings
    
    # Check if force sync mode is enabled
    force_sync = getattr(settings, 'NOTIFICATION_FORCE_SYNC', True)
    if force_sync:
        logger.info(f"[NOTIFY_USER] Force sync mode enabled, skipping async for user={user}")
        use_async = False
    
    try:
        if use_async:
            # Try to send via Celery (async)
            try:
                notify_user_task.delay(
                    user=user,
                    title_en=title_en,
                    title_ar=title_ar,
                    desc_ar=desc_ar,
                    desc_en=desc_en,
                    locale=locale,
                    mobile_url=mobile_url,
                    web_url=web_url,
                    notification_type=notification_type,
                    trip_id=trip_id
                )
                logger.info(f"[NOTIFY_USER] Notification queued successfully via Celery for user={user}")
                return True
            except Exception as e:
                # Celery/Redis unavailable or worker not running, fall back to sync
                error_msg = str(e)
                if 'Connection refused' in error_msg or '6379' in error_msg:
                    logger.warning(f"[NOTIFY_USER] Celery/Redis unavailable (Connection refused). Falling back to synchronous notification.")
                elif 'No active workers' in error_msg or 'worker' in error_msg.lower():
                    logger.warning(f"[NOTIFY_USER] Celery worker not running. Falling back to synchronous notification.")
                else:
                    logger.warning(f"[NOTIFY_USER] Failed to queue via Celery: {e}. Falling back to synchronous notification.")
                
                # Fall through to sync execution
        
        # Send synchronously (either as fallback or if use_async=False)
        logger.info(f"[NOTIFY_USER] Sending notification synchronously for user={user}")
        notify_user_sync(
            user=user,
            title_en=title_en,
            title_ar=title_ar,
            desc_ar=desc_ar,
            desc_en=desc_en,
            locale=locale,
            mobile_url=mobile_url,
            web_url=web_url,
            notification_type=notification_type,
            trip_id=trip_id
        )
        return True
        
    except Exception as e:
        logger.error(f"[NOTIFY_USER] Failed to send notification (both async and sync failed): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def notify_all_drivers(title_en, title_ar, desc_en, desc_ar, locale='en', mobile_url=None, web_url=None, trip_id=None, notification_type=None):
    """
    Notify all active drivers with device tokens about a new trip request.
    
    Args:
        title_en: Notification title in English
        title_ar: Notification title in Arabic
        desc_en: Notification description in English
        desc_ar: Notification description in Arabic
        locale: Default locale ('en' or 'ar')
        mobile_url: Optional mobile app deep link
        web_url: Optional web URL
        trip_id: Optional trip ID for deep linking
        notification_type: Type of notification (defaults to NEW_TRIP_REQUEST if not provided)
    
    Returns:
        dict with success_count, failure_count, total_drivers
    """
    from django.contrib.auth import get_user_model
    from apps.accounts.models import FCMDevice
    from apps.drivers.models import NormalDriver
    from django.conf import settings
    
    User = get_user_model()
    
    # Get all active normal drivers with device tokens
    drivers_with_tokens = User.objects.filter(
        account_type='normal_driver',
        is_active=True,
        is_profile_completed=True,
        devices__isnull=False
    ).distinct()
    
    total_drivers = drivers_with_tokens.count()
    success_count = 0
    failure_count = 0
    
    logger.info(f"[NOTIFY_ALL_DRIVERS] Attempting to notify {total_drivers} drivers about new trip")
    
    if total_drivers == 0:
        logger.warning("[NOTIFY_ALL_DRIVERS] No drivers with device tokens found")
        return {
            'success_count': 0,
            'failure_count': 0,
            'total_drivers': 0
        }
    
    # Build mobile_url with trip_id if provided
    final_mobile_url = mobile_url
    if trip_id and not final_mobile_url:
        final_mobile_url = f"trips://new-requests?trip_id={trip_id}"
    
    # Check if force sync mode is enabled (for production when Celery worker is not running)
    force_sync = getattr(settings, 'NOTIFICATION_FORCE_SYNC', True)
    
    # Send notification to each driver
    for driver in drivers_with_tokens:
        try:
            result = notify_user(
                user=driver.id,
                title_en=title_en,
                title_ar=title_ar,
                desc_en=desc_en,
                desc_ar=desc_ar,
                locale=locale,
                mobile_url=final_mobile_url,
                web_url=web_url,
                use_async=not force_sync,  # Use sync if force_sync is enabled
                notification_type=notification_type or NOTIFICATION_TYPE_NEW_TRIP_REQUEST,
                trip_id=trip_id
            )
            if result:
                success_count += 1
            else:
                failure_count += 1
                logger.warning(f"[NOTIFY_ALL_DRIVERS] Failed to notify driver {driver.id} ({driver.email})")
        except Exception as e:
            failure_count += 1
            logger.error(f"[NOTIFY_ALL_DRIVERS] Error notifying driver {driver.id} ({driver.email}): {str(e)}")
    
    logger.info(f"[NOTIFY_ALL_DRIVERS] Completed. Success: {success_count}, Failures: {failure_count}, Total: {total_drivers}")
    
    return {
        'success_count': success_count,
        'failure_count': failure_count,
        'total_drivers': total_drivers
    }


