import json
import os

import redis
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models.trip import Trip
from utils.common.jwt_utils import get_user_from_access_token


ALLOWED_TRACKING_STATUSES = ["driver_on_the_way", "active"]


def _get_redis_connection() -> redis.Redis:
    """
    إرجاع اتصال Redis متزامن بسيط لتخزين آخر موقع للرحلة.
    """
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.from_url(redis_url)


class TripTrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket لمتابعة موقع السائق في الرحلة.

    - السائق يرسل تحديثات الموقع (type=location_update).
    - الركاب / لوحة التحكم يستقبلون تحديثات الموقع فقط.
    - يتم تخزين آخر موقع في Redis تحت المفتاح: trip_tracking:<trip_id>
    - يتم حذف البيانات عند اكتمال الرحلة أو إلغائها من خدمة منفصلة.
    """

    async def connect(self):
        self.trip_id = self.scope["url_route"]["kwargs"]["trip_id"]
        self.group_name = f"trip_tracking_{self.trip_id}"
        self.user = None
        self.is_authenticated_driver = False

        trip_ok = await self._is_trip_trackable()
        if not trip_ok:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        last_location = await self._get_last_location()
        if last_location:
            await self.send_json({
                "type": "location",
                "location": last_location,
            })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """
        نتوقع رسائل من السائق فقط بالشكل التالي:
        {
          "type": "location_update",
          "lat": 12.34,
          "lng": 56.78,
          "heading": 90,  # اختياري
          "speed": 30     # اختياري
        }
        """
        msg_type = content.get("type")

        if msg_type == "driver_auth":
            access = content.get("access") or content.get("token")
            if not access:
                await self.send_json({"type": "auth_error"})
                return

            user = await sync_to_async(get_user_from_access_token)(access)
            if not user:
                await self.send_json({"type": "auth_error"})
                return

            self.user = user

            is_driver = await self._is_driver_for_trip()
            if not is_driver:
                await self.send_json({"type": "auth_error"})
                return

            self.is_authenticated_driver = True
            await self.send_json({"type": "auth_ok"})
            return

        if msg_type == "location_update":
            if not self.is_authenticated_driver:
                return

            lat = content.get("lat")
            lng = content.get("lng")
            if lat is None or lng is None:
                return

            location = {
                "lat": lat,
                "lng": lng,
                "heading": content.get("heading"),
                "speed": content.get("speed"),
            }

            await self._set_last_location(location)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "trip.location",  # تنادي trip_location
                    "location": location,
                },
            )

    async def trip_location(self, event):
        """يتم استدعاؤها عندما يأتي تحديث موقع جديد عبر group_send."""
        await self.send_json({
            "type": "location",
            "location": event["location"],
        })

    async def trip_ended(self, event):
        """
        يتم استدعاؤها من خدمة خارجية عندما تنتهي الرحلة (completed أو cancelled).
        """
        await self.send_json({
            "type": "ended",
            "reason": event.get("reason"),
        })
        await self.close()

    # ====== Helpers (DB + Redis) ======

    async def _is_trip_trackable(self) -> bool:
        @sync_to_async
        def check():
            try:
                trip = Trip.objects.get(pk=self.trip_id)
                return trip.status in ALLOWED_TRACKING_STATUSES
            except Trip.DoesNotExist:
                return False

        return await check()

    async def _is_driver_for_trip(self) -> bool:
        """
        التأكد أن المستخدم الحالي هو السائق المرتبط بالرحلة.
        نعتمد على أن BaseDriver مرتبط بـ CustomUser عن طريق الحقل user.
        """
        user = getattr(self, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False

        @sync_to_async
        def check():
            try:
                trip = Trip.objects.select_related("base_driver__user").get(pk=self.trip_id)
            except Trip.DoesNotExist:
                return False

            if not trip.base_driver or not hasattr(trip.base_driver, "user"):
                return False

            return trip.base_driver.user_id == user.id

        return await check()

    async def _get_last_location(self):
        conn = _get_redis_connection()
        key = f"trip_tracking:{self.trip_id}"

        def _get():
            data = conn.get(key)
            if not data:
                return None
            try:
                if isinstance(data, bytes):
                    data_str = data.decode("utf-8")
                else:
                    data_str = data
                return json.loads(data_str)
            except Exception:
                return None

        return await sync_to_async(_get)()

    async def _set_last_location(self, location: dict):
        conn = _get_redis_connection()
        key = f"trip_tracking:{self.trip_id}"

        def _set():
            conn.set(key, json.dumps(location), ex=60 * 60)

        await sync_to_async(_set)()


