import json
import math
import os

import redis
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models.trip import Trip
from utils.common.jwt_utils import get_user_from_access_token


ALLOWED_TRACKING_STATUSES = ["driver_on_the_way", "active"]
LOCATION_MAX_AGE_SECONDS = 30


def _get_redis_connection() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.from_url(redis_url)


def _coordinate(value, minimum, maximum):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and minimum <= value <= maximum
    except (TypeError, ValueError, OverflowError):
        return False


def _fresh_location(location):
    if not isinstance(location, dict):
        return False
    if not _coordinate(location.get("lat"), -90, 90):
        return False
    if not _coordinate(location.get("lng"), -180, 180):
        return False
    received_at = location.get("received_at")
    if not isinstance(received_at, str):
        return False
    try:
        received = parse_datetime(received_at)
    except (TypeError, ValueError):
        return False
    if received is None or timezone.is_naive(received):
        return False
    age = (timezone.now() - received).total_seconds()
    return 0 <= age < LOCATION_MAX_AGE_SECONDS


class TripTrackingConsumer(AsyncJsonWebsocketConsumer):
    """The existing trip stream, restricted to its driver and authorised viewers.

    Opening a transport grants no subscription and reveals no cached location.
    The existing mobile driver_auth exchange is preserved. Website viewers send
    viewer_auth with their existing access token; both roles receive auth_ok.
    """

    async def connect(self):
        self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
        self.group_name = f"trip_tracking_{self.trip_id}"
        self.access_token = None
        self.role = None
        self.joined_group = False
        self.stopped = False
        await self.accept()

    async def disconnect(self, close_code):
        self.stopped = True
        await self._clear_authentication()

    async def receive_json(self, content, **kwargs):
        if self.stopped:
            return
        if not isinstance(content, dict):
            await self._deny()
            return

        msg_type = content.get("type")
        if msg_type in ("driver_auth", "viewer_auth"):
            await self._clear_authentication()
            access = content.get("access") or content.get("token")
            role = "driver" if msg_type == "driver_auth" else "viewer"
            details = await self._access_details(access, role)
            if details is None:
                await self._deny()
                return

            self.access_token = access
            self.role = role
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            self.joined_group = True

            # Assignment, status or account permission may change while joining.
            details = await self._current_access()
            if details is None:
                await self._deny()
                return
            await self.send_json({"type": "auth_ok", "role": role})
            last_location = await self._get_last_location(details["driver_id"])
            if last_location is not None:
                await self._send_location(last_location, details["driver_id"])
            return

        if msg_type == "location_update":
            if self.role != "driver":
                await self._deny()
                return
            details = await self._current_access()
            if details is None:
                await self._deny()
                return

            lat, lng = content.get("lat"), content.get("lng")
            if not _coordinate(lat, -90, 90) or not _coordinate(lng, -180, 180):
                return
            heading, speed = content.get("heading"), content.get("speed")
            location = {
                "lat": lat,
                "lng": lng,
                "heading": heading if _coordinate(heading, 0, 360) else None,
                "speed": speed if _coordinate(speed, 0, float("inf")) else None,
                # Server receipt time, not a replacement for the mobile GPS-age check.
                "received_at": timezone.now().isoformat(),
            }
            await self._set_last_location(location, details["driver_id"])

            current = await self._current_access()
            if current is None or current["driver_id"] != details["driver_id"]:
                await self._deny()
                return
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "trip.location",
                    "location": location,
                    "driver_id": details["driver_id"],
                },
            )

    async def trip_location(self, event):
        await self._send_location(event.get("location"), event.get("driver_id"))

    async def trip_ended(self, event):
        if self.stopped or self.role is None:
            return
        self.stopped = True
        await self._clear_authentication()
        await self.send_json({"type": "ended", "reason": event.get("reason")})
        await self.close()

    async def _send_location(self, location, driver_id):
        if self.stopped or self.role is None:
            return
        details = await self._current_access()
        if details is None:
            await self._deny()
            return
        # A late event/cache entry from a previous assignment is not current GPS.
        if driver_id is None or driver_id != details["driver_id"]:
            return
        if _fresh_location(location):
            await self.send_json({"type": "location", "location": location})

    async def _current_access(self):
        if self.stopped or self.role is None:
            return None
        return await self._access_details(self.access_token, self.role)

    @database_sync_to_async
    def _access_details(self, access, role):
        if not isinstance(access, str) or not access or len(access) > 8192:
            return None
        try:
            user = get_user_from_access_token(access)
        except (TypeError, ValueError, OverflowError):
            return None
        if not user or not user.is_authenticated or not user.is_active:
            return None
        try:
            trip = Trip.objects.select_related("base_driver", "passenger").get(
                pk=self.trip_id,
                status__in=ALLOWED_TRACKING_STATUSES,
            )
        except Trip.DoesNotExist:
            return None

        allowed = False
        if role == "driver":
            allowed = (
                user.account_type in ("normal_driver", "office_driver")
                and user.is_profile_completed
                and user.is_admin_verified
                and trip.base_driver is not None
                and trip.base_driver.user_id == user.id
            )
        elif role == "viewer":
            if user.is_staff:
                allowed = True
            elif (
                user.account_type == "passenger"
                and user.is_profile_completed
                and user.is_admin_verified
                and hasattr(user, "passenger_profile")
            ):
                # Preserve the existing passenger REST ownership/email fallback.
                allowed = trip.passenger_id == user.passenger_profile.id or bool(
                    user.email
                    and trip.passenger_email
                    and user.email.lower() == trip.passenger_email.lower()
                )
        if not allowed:
            return None
        return {"driver_id": trip.base_driver_id}

    async def _clear_authentication(self):
        self.access_token = None
        self.role = None
        if self.joined_group:
            self.joined_group = False
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def _deny(self):
        self.stopped = True
        await self._clear_authentication()
        await self.send_json({"type": "auth_error"})
        await self.close(code=4403)

    async def _get_last_location(self, driver_id):
        if driver_id is None:
            return None
        conn = _get_redis_connection()
        key = f"trip_tracking:{self.trip_id}"

        def get():
            data = conn.get(key)
            if not data:
                return None
            try:
                cached = json.loads(data)
            except (TypeError, ValueError, UnicodeDecodeError):
                return None
            if not isinstance(cached, dict) or cached.get("driver_id") != driver_id:
                return None
            location = cached.get("location")
            return location if _fresh_location(location) else None

        return await sync_to_async(get)()

    async def _set_last_location(self, location, driver_id):
        conn = _get_redis_connection()
        key = f"trip_tracking:{self.trip_id}"
        cached = {"driver_id": driver_id, "location": location}
        await sync_to_async(conn.set)(
            key, json.dumps(cached), ex=LOCATION_MAX_AGE_SECONDS
        )


