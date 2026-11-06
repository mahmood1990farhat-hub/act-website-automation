"""Exercise the real consumer, URL routing, JWT validation and database models.

Only Redis storage is replaced with a local dictionary. No payment, email,
notification or external tracking endpoints are called.
"""

import functools
import json
from datetime import date, time, timedelta
from unittest.mock import Mock, patch

from asgiref.sync import sync_to_async
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.drivers.models import BaseDriver
from apps.passengers.models import Passenger
from apps.trips.consumers import LOCATION_MAX_AGE_SECONDS
from apps.trips.models import Trip
from apps.trips.routing import websocket_urlpatterns
from apps.trips.services.trip_tracking import stop_trip_tracking


def socket_case(method):
    """Close ASGI tasks in their original loop even when an assertion fails."""
    @functools.wraps(method)
    async def run(self):
        try:
            await method(self)
        finally:
            for connection in self.connections:
                await connection.disconnect()
            await get_channel_layer().flush()
    return run


class TripTrackingAccessTests(TransactionTestCase):
    def setUp(self):
        self.connections = []
        self.cached = {}
        self.redis = Mock()
        self.redis.get.side_effect = self.cached.get
        self.redis.set.side_effect = lambda key, data, **kwargs: self.cached.update({key: data})
        self.redis.delete.side_effect = lambda key: self.cached.pop(key, None)
        redis_patch = patch("apps.trips.consumers._get_redis_connection", return_value=self.redis)
        self.redis_factory = redis_patch.start()
        self.addCleanup(redis_patch.stop)
        stop_patch = patch("apps.trips.services.trip_tracking._get_redis_connection", return_value=self.redis)
        stop_patch.start()
        self.addCleanup(stop_patch.stop)

        self.passenger = self.user("owner", "passenger")
        self.passenger_profile = Passenger.objects.create(user=self.passenger)
        self.other_passenger = self.user("other", "passenger")
        self.other_profile = Passenger.objects.create(user=self.other_passenger)
        self.staff = self.user("staff", "admin", is_staff=True)
        self.nonstaff = self.user("nonstaff", "admin")
        self.driver_user = self.user("driver", "normal_driver")
        self.other_driver_user = self.user("other-driver", "normal_driver")
        self.driver = BaseDriver.objects.create(user=self.driver_user)
        self.other_driver = BaseDriver.objects.create(user=self.other_driver_user)
        self.trip = Trip.objects.create(
            pickup_lat=51.47,
            pickup_lng=-0.45,
            dropoff_lat=51.50,
            dropoff_lng=-0.12,
            trip_date=date.today(),
            trip_time=time(12),
            cost="12.00",
            passengers_count=1,
            passenger=self.passenger_profile,
            passenger_email=self.passenger.email,
            base_driver=self.driver,
            status="driver_on_the_way",
            is_paid=True,
        )
        self.key = f"trip_tracking:{self.trip.pk}"
        expired = AccessToken.for_user(self.passenger)
        expired.set_exp(from_time=timezone.now(), lifetime=timedelta(seconds=-5))
        self.expired_token = str(expired)
        self.refresh_token = str(RefreshToken.for_user(self.passenger))

    def user(self, name, account_type, **extra):
        return get_user_model().objects.create_user(
            username=name,
            email=f"{name}@example.invalid",
            password="isolated-tracking-test-password",
            first_name="Test",
            last_name=name,
            address="Test",
            phone_number="",
            account_type=account_type,
            is_active=True,
            is_profile_completed=True,
            is_admin_verified=True,
            **extra,
        )

    def token(self, user):
        return str(AccessToken.for_user(user))

    def location(self, **overrides):
        return {
            "lat": 51.48,
            "lng": -0.44,
            "heading": 90,
            "speed": 8,
            "received_at": timezone.now().isoformat(),
            **overrides,
        }

    async def connect(self, trip_id=None):
        connection = WebsocketCommunicator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
            f"/ws/trips/{trip_id or self.trip.pk}/tracking/",
        )
        self.connections.append(connection)
        connected, _ = await connection.connect()
        self.assertTrue(connected)
        return connection

    async def authenticate(self, connection, user, role="viewer", field="access"):
        await connection.send_json_to({"type": f"{role}_auth", field: self.token(user)})
        self.assertEqual(await connection.receive_json_from(), {"type": "auth_ok", "role": role})

    async def denied(self, connection):
        self.assertEqual(await connection.receive_json_from(), {"type": "auth_error"})
        self.assertEqual(await connection.receive_output(), {"type": "websocket.close", "code": 4403})

    async def broadcast(self, location=None, driver_id=None):
        await get_channel_layer().group_send(
            f"trip_tracking_{self.trip.pk}",
            {
                "type": "trip.location",
                "location": location or self.location(),
                "driver_id": driver_id or self.driver.pk,
            },
        )

    async def update_trip(self, **changes):
        await database_sync_to_async(Trip.objects.filter(pk=self.trip.pk).update)(**changes)

    async def update_user(self, user, **changes):
        await database_sync_to_async(get_user_model().objects.filter(pk=user.pk).update)(**changes)

    @socket_case
    async def test_opening_transport_does_not_read_cache_or_subscribe(self):
        self.cached[self.key] = json.dumps({"driver_id": self.driver.pk, "location": self.location()})
        connection = await self.connect()
        await self.broadcast()
        self.assertTrue(await connection.receive_nothing(timeout=0.05))
        self.redis_factory.assert_not_called()
        self.assertFalse(get_channel_layer().groups.get(f"trip_tracking_{self.trip.pk}"))

    @socket_case
    async def test_owner_and_real_staff_receive_after_authentication(self):
        owner = await self.connect()
        staff = await self.connect()
        await self.authenticate(owner, self.passenger)
        await self.authenticate(staff, self.staff)
        location = self.location()
        await self.broadcast(location)
        for connection in (owner, staff):
            self.assertEqual(await connection.receive_json_from(), {"type": "location", "location": location})

    @socket_case
    async def test_existing_passenger_email_fallback_remains_authorised(self):
        await self.update_trip(passenger=None, passenger_email=self.passenger.email.upper(), is_guest_checkout=True)
        connection = await self.connect()
        await self.authenticate(connection, self.passenger)
        await self.broadcast()
        self.assertEqual((await connection.receive_json_from())["type"], "location")

    @socket_case
    async def test_unrelated_passenger_nonstaff_and_other_driver_cannot_view(self):
        for user in (self.other_passenger, self.nonstaff, self.other_driver_user):
            with self.subTest(user=user.username):
                connection = await self.connect()
                await connection.send_json_to({"type": "viewer_auth", "access": self.token(user)})
                await self.denied(connection)
        self.redis_factory.assert_not_called()

    @socket_case
    async def test_missing_invalid_expired_and_refresh_tokens_reveal_no_cache(self):
        for token in (None, "invalid-token", self.expired_token, self.refresh_token):
            with self.subTest(token_kind="missing" if token is None else "invalid_or_expired"):
                connection = await self.connect()
                await connection.send_json_to({"type": "viewer_auth", "access": token})
                await self.denied(connection)
        self.redis_factory.assert_not_called()

    @socket_case
    async def test_inactive_unapproved_and_incomplete_accounts_are_refused(self):
        for changes in ({"is_active": False}, {"is_admin_verified": False}, {"is_profile_completed": False}):
            with self.subTest(changes=changes):
                await self.update_user(self.passenger, is_active=True, is_admin_verified=True, is_profile_completed=True)
                await self.update_user(self.passenger, **changes)
                connection = await self.connect()
                await connection.send_json_to({"type": "viewer_auth", "access": self.token(self.passenger)})
                await self.denied(connection)
        self.redis_factory.assert_not_called()

    @socket_case
    async def test_assigned_driver_existing_protocol_publishes_timestamped_locations(self):
        driver = await self.connect()
        viewer = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver", "token")
        await self.authenticate(viewer, self.passenger)
        before = timezone.now()
        await driver.send_json_to({"type": "location_update", "lat": 0, "lng": 0, "heading": 90, "speed": 8, "received_at": "old-client-value"})
        location = (await viewer.receive_json_from())["location"]
        self.assertEqual((location["lat"], location["lng"], location["heading"], location["speed"]), (0, 0, 90, 8))
        self.assertGreaterEqual(parse_datetime(location["received_at"]), before)
        self.assertEqual((await driver.receive_json_from())["location"], location)
        self.assertEqual(self.redis.set.call_args.kwargs, {"ex": LOCATION_MAX_AGE_SECONDS})
        self.assertEqual(json.loads(self.cached[self.key]), {"driver_id": self.driver.pk, "location": location})

    @socket_case
    async def test_unassigned_driver_and_viewer_cannot_publish(self):
        other_driver = await self.connect()
        await other_driver.send_json_to({"type": "driver_auth", "access": self.token(self.other_driver_user)})
        await self.denied(other_driver)
        viewer = await self.connect()
        await self.authenticate(viewer, self.passenger)
        await viewer.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
        await self.denied(viewer)
        self.redis.set.assert_not_called()

    @socket_case
    async def test_fresh_cache_is_delivered_only_after_auth_ok(self):
        location = self.location()
        self.cached[self.key] = json.dumps({"driver_id": self.driver.pk, "location": location})
        connection = await self.connect()
        self.assertTrue(await connection.receive_nothing(timeout=0.05))
        await self.authenticate(connection, self.passenger)
        self.assertEqual(await connection.receive_json_from(), {"type": "location", "location": location})
        self.redis.set.assert_not_called()

    @socket_case
    async def test_legacy_expired_future_or_previous_driver_cache_is_not_fresh(self):
        now = timezone.now()
        cases = [
            self.location(),  # The old unbound cache format is never accepted.
            {"driver_id": self.driver.pk, "location": {"lat": 51, "lng": -0.5}},
            {"driver_id": self.driver.pk, "location": self.location(received_at=(now - timedelta(seconds=31)).isoformat())},
            {"driver_id": self.driver.pk, "location": self.location(received_at=(now + timedelta(minutes=1)).isoformat())},
            {"driver_id": self.other_driver.pk, "location": self.location()},
        ]
        for index, cached in enumerate(cases):
            with self.subTest(cache_case=index):
                self.cached[self.key] = json.dumps(cached)
                connection = await self.connect()
                await self.authenticate(connection, self.passenger)
                self.assertTrue(await connection.receive_nothing(timeout=0.05))
        self.redis.set.assert_not_called()

    @socket_case
    async def test_permission_revocation_is_checked_before_next_delivery(self):
        owner = await self.connect()
        staff = await self.connect()
        await self.authenticate(owner, self.passenger)
        await self.authenticate(staff, self.staff)
        await self.update_user(self.passenger, is_active=False)
        await self.update_user(self.staff, is_staff=False)
        await self.broadcast()
        await self.denied(owner)
        await self.denied(staff)

    @socket_case
    async def test_passenger_ownership_change_blocks_existing_viewer(self):
        owner = await self.connect()
        await self.authenticate(owner, self.passenger)
        await self.update_trip(passenger=self.other_profile, passenger_email=self.other_passenger.email)
        await self.broadcast()
        await self.denied(owner)

    @socket_case
    async def test_reassignment_blocks_old_driver_and_late_old_assignment_data(self):
        old_driver = await self.connect()
        viewer = await self.connect()
        await self.authenticate(old_driver, self.driver_user, "driver")
        await self.authenticate(viewer, self.passenger)
        await self.update_trip(base_driver=self.other_driver)
        await old_driver.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
        await self.denied(old_driver)
        self.redis.set.assert_not_called()
        await self.broadcast(driver_id=self.driver.pk)
        self.assertTrue(await viewer.receive_nothing(timeout=0.05))
        new_driver = await self.connect()
        await self.authenticate(new_driver, self.other_driver_user, "driver")
        await new_driver.send_json_to({"type": "location_update", "lat": 52, "lng": -0.2})
        self.assertEqual((await viewer.receive_json_from())["location"]["lat"], 52)
        self.assertEqual((await new_driver.receive_json_from())["location"]["lat"], 52)

    @socket_case
    async def test_expiry_after_handshake_blocks_publish_and_delivery(self):
        driver = await self.connect()
        viewer = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver")
        await self.authenticate(viewer, self.passenger)
        # Advance the actual SimpleJWT validator clock, without mocking validation.
        with patch("rest_framework_simplejwt.tokens.aware_utcnow", return_value=timezone.now() + timedelta(days=2)):
            await driver.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
            await self.denied(driver)
            await self.broadcast()
            await self.denied(viewer)
        self.redis.set.assert_not_called()

    @socket_case
    async def test_terminal_or_ineligible_trip_state_blocks_publication_and_new_auth(self):
        for trip_status in ("completed", "cancelled", "pending", "accepted", "expired"):
            with self.subTest(trip_status=trip_status):
                await self.update_trip(status="active")
                driver = await self.connect()
                await self.authenticate(driver, self.driver_user, "driver")
                await self.update_trip(status=trip_status)
                await driver.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
                await self.denied(driver)
                viewer = await self.connect()
                await viewer.send_json_to({"type": "viewer_auth", "access": self.token(self.passenger)})
                await self.denied(viewer)
        self.redis.set.assert_not_called()

    @socket_case
    async def test_driver_approval_revoked_after_handshake_blocks_publication(self):
        driver = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver")
        await self.update_user(self.driver_user, is_admin_verified=False)
        await driver.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
        await self.denied(driver)
        self.redis.set.assert_not_called()

    @socket_case
    async def test_failed_reauthentication_does_not_keep_previous_subscription(self):
        driver = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver")
        await driver.send_json_to({"type": "driver_auth", "access": "invalid-token"})
        await self.denied(driver)
        self.assertFalse(get_channel_layer().groups.get(f"trip_tracking_{self.trip.pk}"))
        await self.broadcast()
        self.assertTrue(await driver.receive_nothing(timeout=0.05))

    @socket_case
    async def test_existing_stop_service_ends_stream_and_discards_late_updates(self):
        driver = await self.connect()
        viewer = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver")
        await self.authenticate(viewer, self.passenger)
        await driver.send_json_to({"type": "location_update", "lat": 51, "lng": -0.5})
        for connection in (driver, viewer):
            self.assertEqual((await connection.receive_json_from())["type"], "location")
        await self.update_trip(status="completed")
        await sync_to_async(stop_trip_tracking)(self.trip.pk, reason="completed")
        for connection in (driver, viewer):
            self.assertEqual(await connection.receive_json_from(), {"type": "ended", "reason": "completed"})
            self.assertEqual((await connection.receive_output())["type"], "websocket.close")
        self.assertNotIn(self.key, self.cached)
        await driver.send_json_to({"type": "location_update", "lat": 52, "lng": -0.3})
        await self.broadcast()
        for connection in (driver, viewer):
            self.assertTrue(await connection.receive_nothing(timeout=0.05))
        self.assertEqual(self.redis.set.call_count, 1)

    @socket_case
    async def test_invalid_coordinates_do_not_create_location_records(self):
        driver = await self.connect()
        await self.authenticate(driver, self.driver_user, "driver")
        for lat, lng in ((True, 0), (91, 0), (0, -181), ("51", 0), (None, 0), (float("nan"), 0), (10 ** 400, 0)):
            await driver.send_json_to({"type": "location_update", "lat": lat, "lng": lng})
        # The valid final message also establishes that prior queued messages ran.
        await driver.send_json_to({"type": "location_update", "lat": 0, "lng": 0})
        self.assertEqual((await driver.receive_json_from())["location"]["lat"], 0)
        self.assertEqual(self.redis.set.call_count, 1)
