import json
import os

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _get_redis_connection() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.from_url(redis_url)


def stop_trip_tracking(trip_id: int, reason: str | None = None) -> None:
    """
    إيقاف تتبع رحلة معيّنة:
    - حذف آخر موقع من Redis.
    - إرسال رسالة لكل الـ WebSocket clients بأن الرحلة انتهت.
    """
    conn = _get_redis_connection()
    key = f"trip_tracking:{trip_id}"
    try:
        conn.delete(key)
    except Exception:
        pass

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"trip_tracking_{trip_id}",
            {
                "type": "trip.ended",
                "reason": reason,
            },
        )
    except Exception:
        pass


