"""
Demo / development database seeding helpers.

Used by management commands (seed_demo, seed_vehicle_types, seed_airports).
Keep data idempotent via get_or_create / update_or_create on stable keys.
"""
from __future__ import annotations

import base64
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from apps.drivers.models import BaseDriver, NormalDriver
from apps.office.models import Office
from apps.passengers.models import Passenger
from apps.trips.models import Airport, StopPoint, Trip
from apps.vehicle.models import Vehicle, VehicleType
from utils.calculate_cost import PRICING

User = get_user_model()

# 1×1 transparent PNG (no Pillow dependency)
_MIN_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
MINIMAL_PNG_BYTES = base64.b64decode(_MIN_PNG_B64)

# Minimal PDF bytes sufficient for storage / dev uploads
DUMMY_PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _png_file(name: str = "icon.png") -> ContentFile:
    return ContentFile(MINIMAL_PNG_BYTES, name=name)


def _pdf_file(name: str = "document.pdf") -> ContentFile:
    return ContentFile(DUMMY_PDF_BYTES, name=name)


DEMO_PASSWORD = "DemoPass123!"

DEMO_USERS = (
    {
        "key": "passenger",
        "email": "demo.passenger@example.com",
        "username": "demo_passenger",
        "first_name": "Demo",
        "last_name": "Passenger",
        "phone": "+447700900001",
        "account_type": "passenger",
        "address": "10 Demo Street, London, UK",
    },
    {
        "key": "passenger_2",
        "email": "demo.passenger2@example.com",
        "username": "demo_passenger_2",
        "first_name": "Demo",
        "last_name": "PassengerTwo",
        "phone": "+447700900004",
        "account_type": "passenger",
        "address": "11 Demo Street, London, UK",
    },
    {
        "key": "office_owner",
        "email": "demo.office@example.com",
        "username": "demo_office",
        "first_name": "Demo",
        "last_name": "OfficeOwner",
        "phone": "+447700900002",
        "account_type": "office_owner",
        "address": "20 Fleet Street, London, UK",
    },
    {
        "key": "driver",
        "email": "demo.driver@example.com",
        "username": "demo_driver",
        "first_name": "Demo",
        "last_name": "Driver",
        "phone": "+447700900003",
        "account_type": "normal_driver",
        "address": "30 Driver Road, London, UK",
    },
    {
        "key": "driver_2",
        "email": "demo.driver2@example.com",
        "username": "demo_driver_2",
        "first_name": "Demo",
        "last_name": "DriverTwo",
        "phone": "+447700900005",
        "account_type": "normal_driver",
        "address": "31 Driver Road, London, UK",
    },
)


def seed_vehicle_types(stdout, style, dry_run: bool = False) -> int:
    """Create VehicleType rows for every key in utils.calculate_cost.PRICING."""
    count = 0
    for order, (name_en, _data) in enumerate(PRICING.items()):
        name_ar = name_en
        desc_en = f"Seeded vehicle type: {name_en}"
        desc_ar = desc_en
        if dry_run:
            stdout.write(f"  [dry-run] VehicleType: {name_en}")
            count += 1
            continue
        _, created = VehicleType.objects.update_or_create(
            name_en=name_en,
            defaults={
                "name_ar": name_ar,
                "desc_en": desc_en,
                "desc_ar": desc_ar,
                "icon": _png_file(f"vt_{order}.png"),
                "max_passengers_count": 4 if "7" not in name_en and "Van" not in name_en else 7,
                "order": order,
            },
        )
        if created:
            count += 1
        stdout.write(f"  VehicleType: {name_en} ({'created' if created else 'updated'})")
    stdout.write(style.SUCCESS(f"Vehicle types: {len(PRICING)} ensured, {count} newly created"))
    return count


def seed_airports(stdout, style, dry_run: bool = False) -> int:
    """Create a few UK airports with simple bounding polygons (SRID 4326)."""
    from django.contrib.gis.geos import Polygon

    specs = (
        {
            "name_en": "London Heathrow (LHR)",
            "name_ar": "مطار هيثرو لندن",
            "pickup_vat": 0.20,
            "dropoff_vat": 0.20,
            "bbox": (-0.52, 51.44, -0.38, 51.50),
        },
        {
            "name_en": "London Gatwick (LGW)",
            "name_ar": "مطار غاتويك لندن",
            "pickup_vat": 0.20,
            "dropoff_vat": 0.20,
            "bbox": (-0.20, 51.14, -0.12, 51.20),
        },
    )
    created_n = 0
    for spec in specs:
        xmin, ymin, xmax, ymax = spec["bbox"]
        poly = Polygon.from_bbox((xmin, ymin, xmax, ymax))
        poly.srid = 4326
        if dry_run:
            stdout.write(f"  [dry-run] Airport: {spec['name_en']}")
            continue
        obj, created = Airport.objects.update_or_create(
            name_en=spec["name_en"],
            defaults={
                "name_ar": spec["name_ar"],
                "pickup_vat": spec["pickup_vat"],
                "dropoff_vat": spec["dropoff_vat"],
                "detection_area": poly,
                "is_active": True,
                "vehicle_specific_fees": {},
            },
        )
        if created:
            created_n += 1
        stdout.write(f"  Airport: {obj.name_en} ({'created' if created else 'updated'})")
    stdout.write(style.SUCCESS(f"Airports: {len(specs)} ensured, {created_n} newly created"))
    return created_n


def seed_demo_users(stdout, style, dry_run: bool = False) -> dict:
    """Create demo CustomUser rows plus Passenger and Office where applicable."""
    refs: dict = {}
    if dry_run:
        for u in DEMO_USERS:
            stdout.write(f"  [dry-run] User: {u['email']}")
        return refs

    for spec in DEMO_USERS:
        user, created = User.objects.update_or_create(
            email=spec["email"],
            defaults={
                "username": spec["username"],
                "first_name": spec["first_name"],
                "last_name": spec["last_name"],
                "phone_number": spec["phone"],
                "account_type": spec["account_type"],
                "address": spec["address"],
                "is_active": True,
                "is_profile_completed": True,
                "is_admin_verified": True,
            },
        )
        user.set_password(DEMO_PASSWORD)
        user.save(update_fields=["password"])
        if created:
            stdout.write(style.SUCCESS(f"  User created: {user.email}"))
        else:
            stdout.write(f"  User updated: {user.email}")

        if spec["key"] == "passenger":
            Passenger.objects.get_or_create(user=user)
            refs["passenger_user"] = user
            refs.setdefault("passenger_users", []).append(user)
        elif spec["key"] == "passenger_2":
            Passenger.objects.get_or_create(user=user)
            refs["passenger_user_2"] = user
            refs.setdefault("passenger_users", []).append(user)
        elif spec["key"] == "office_owner":
            Office.objects.get_or_create(user=user)
            refs["office_user"] = user
        elif spec["key"] == "driver":
            refs["driver_user"] = user
            refs.setdefault("driver_users", []).append(user)
        elif spec["key"] == "driver_2":
            refs["driver_user_2"] = user
            refs.setdefault("driver_users", []).append(user)

    stdout.write(style.SUCCESS("Demo users + Passenger / Office profiles ensured"))
    return refs


def _resolve_vehicle_types():
    preferred_names = ["Standard PHV", "Executive", "MPV", "Executive MPV"]
    resolved = []
    for name in preferred_names:
        vt = VehicleType.objects.filter(name_en=name).first()
        if vt:
            resolved.append(vt)
    if not resolved:
        first_any = VehicleType.objects.order_by("order", "id").first()
        if first_any:
            resolved.append(first_any)
    return resolved


def seed_demo_normal_drivers(stdout, style, driver_users, dry_run: bool = False) -> list:
    """Create multiple NormalDrivers with vehicles and BaseDriver docs."""
    if dry_run:
        stdout.write("  [dry-run] NormalDrivers + Vehicles + BaseDrivers")
        return []
    if not driver_users:
        stdout.write(style.WARNING("  No driver users; skipping driver seed"))
        return []

    vehicle_types = _resolve_vehicle_types()
    if not vehicle_types:
        stdout.write(style.ERROR("  No VehicleType rows found; run vehicle type seed first"))
        return []

    seeded_base_drivers = []
    for idx, driver_user in enumerate(driver_users, start=1):
        vt = vehicle_types[(idx - 1) % len(vehicle_types)]
        vehicle, _ = Vehicle.objects.update_or_create(
            vehicle_number=f"DEMO-PHV-{idx:03d}",
            defaults={
                "year_of_manufacture": 2021 + (idx % 4),
                "vehicle_type": vt,
                "mot": _pdf_file(f"demo_mot_{idx}.pdf"),
                "phv": _pdf_file(f"demo_phv_{idx}.pdf"),
            },
        )

        base, _ = BaseDriver.objects.update_or_create(
            user=driver_user,
            defaults={
                "pco": _pdf_file(f"demo_pco_{idx}.pdf"),
                "dbs": _pdf_file(f"demo_dbs_{idx}.pdf"),
                "dvla": _pdf_file(f"demo_dvla_{idx}.pdf"),
                "stripe_account_id": "",
            },
        )

        NormalDriver.objects.update_or_create(driver=base, defaults={"vehicle": vehicle})
        seeded_base_drivers.append(base)
        stdout.write(style.SUCCESS(f"  Demo normal driver ensured: {driver_user.email} ({vehicle.vehicle_number})"))

    return seeded_base_drivers


def _ensure_trip_stop_points(trip, points):
    existing = list(
        trip.stop_points.order_by("id").values_list("point_str", flat=True)
    )
    target = [p["point_str"] for p in points]
    if existing == target:
        return
    trip.stop_points.all().delete()
    StopPoint.objects.bulk_create(
        [
            StopPoint(
                trip=trip,
                point_lat=p["point_lat"],
                point_lng=p["point_lng"],
                point_str=p["point_str"],
                point_place_id=p.get("point_place_id"),
                point_postal_code=p.get("point_postal_code"),
            )
            for p in points
        ]
    )


def seed_sample_trips(stdout, style, dry_run: bool = False) -> int:
    """Comprehensive sample trips across statuses and assignment scenarios."""
    if dry_run:
        stdout.write("  [dry-run] sample trips")
        return 0

    passenger_users = list(
        User.objects.filter(email__in=["demo.passenger@example.com", "demo.passenger2@example.com"])
    )
    if not passenger_users:
        stdout.write(style.WARNING("  Demo passengers missing; skip trips"))
        return 0

    passengers_map = {
        p.user.email: p for p in Passenger.objects.select_related("user").filter(user__in=passenger_users)
    }
    passenger_primary = passengers_map.get("demo.passenger@example.com")
    passenger_secondary = passengers_map.get("demo.passenger2@example.com")
    if not passenger_primary:
        stdout.write(style.WARNING("  Primary passenger profile missing; skip trips"))
        return 0

    vehicle_types = _resolve_vehicle_types()
    if not vehicle_types:
        stdout.write(style.WARNING("  Vehicle types missing; skip trips"))
        return 0

    base_drivers = list(
        BaseDriver.objects.select_related("user").filter(
            user__email__in=["demo.driver@example.com", "demo.driver2@example.com"]
        )
    )
    primary_driver = next((d for d in base_drivers if d.user.email == "demo.driver@example.com"), None)
    secondary_driver = next((d for d in base_drivers if d.user.email == "demo.driver2@example.com"), None)

    airport = Airport.objects.filter(name_en__icontains="Heathrow").first()
    now_date = date.today()
    samples = (
        {
            "seed_key": "pending-city-hop",
            "passenger": passenger_primary,
            "pickup_lat": 51.5074,
            "pickup_lng": -0.1278,
            "pickup_str": "Charing Cross, London",
            "dropoff_lat": 51.5033,
            "dropoff_lng": -0.1196,
            "dropoff_str": "Waterloo Station, London",
            "trip_date": now_date + timedelta(days=1),
            "trip_time": time(10, 30),
            "status": "pending",
            "is_paid": True,
            "cost": Decimal("45.00"),
            "base_trip_cost": Decimal("36.00"),
            "regular_vat": Decimal("9.00"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 1,
            "base_driver": None,
            "is_guest_driver": False,
            "airport": None,
            "airport_direction": None,
            "distance_miles": 12.5,
            "expected_trip_duration_minutes": 35,
            "stop_points": [],
        },
        {
            "seed_key": "accepted-airport-from",
            "passenger": passenger_primary,
            "pickup_lat": 51.4700,
            "pickup_lng": -0.4543,
            "pickup_str": "Heathrow Terminal 5",
            "dropoff_lat": 51.5074,
            "dropoff_lng": -0.1278,
            "dropoff_str": "Central London",
            "trip_date": now_date + timedelta(days=1),
            "trip_time": time(14, 0),
            "status": "accepted",
            "is_paid": True,
            "cost": Decimal("89.50"),
            "base_trip_cost": Decimal("74.58"),
            "regular_vat": Decimal("14.92"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 2,
            "base_driver": primary_driver,
            "is_guest_driver": False,
            "airport": airport,
            "airport_direction": "from",
            "distance_miles": 18.0,
            "expected_trip_duration_minutes": 55,
            "stop_points": [],
        },
        {
            "seed_key": "driver-on-way-business",
            "passenger": passenger_secondary or passenger_primary,
            "pickup_lat": 51.5154,
            "pickup_lng": -0.0722,
            "pickup_str": "Liverpool Street Station",
            "dropoff_lat": 51.5007,
            "dropoff_lng": -0.1246,
            "dropoff_str": "Westminster, London",
            "trip_date": now_date + timedelta(days=1),
            "trip_time": time(17, 15),
            "status": "driver_on_the_way",
            "is_paid": True,
            "cost": Decimal("72.00"),
            "base_trip_cost": Decimal("60.00"),
            "regular_vat": Decimal("12.00"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 3,
            "base_driver": secondary_driver or primary_driver,
            "is_guest_driver": False,
            "airport": None,
            "airport_direction": None,
            "distance_miles": 10.8,
            "expected_trip_duration_minutes": 44,
            "stop_points": [],
        },
        {
            "seed_key": "active-trip-city",
            "passenger": passenger_secondary or passenger_primary,
            "pickup_lat": 51.5286,
            "pickup_lng": -0.2417,
            "pickup_str": "Wembley Park",
            "dropoff_lat": 51.4700,
            "dropoff_lng": -0.4543,
            "dropoff_str": "Heathrow Terminal 3",
            "trip_date": now_date,
            "trip_time": time(11, 0),
            "status": "active",
            "is_paid": True,
            "cost": Decimal("95.00"),
            "base_trip_cost": Decimal("79.17"),
            "regular_vat": Decimal("15.83"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 4,
            "base_driver": primary_driver or secondary_driver,
            "is_guest_driver": False,
            "airport": airport,
            "airport_direction": "to",
            "distance_miles": 16.9,
            "expected_trip_duration_minutes": 52,
            "stop_points": [
                {
                    "point_lat": 51.5212,
                    "point_lng": -0.1628,
                    "point_str": "Baker Street Stop",
                }
            ],
        },
        {
            "seed_key": "completed-with-stop",
            "passenger": passenger_primary,
            "pickup_lat": 51.5010,
            "pickup_lng": -0.1416,
            "pickup_str": "Victoria Station",
            "dropoff_lat": 51.4700,
            "dropoff_lng": -0.4543,
            "dropoff_str": "Heathrow Terminal 4",
            "trip_date": now_date - timedelta(days=1),
            "trip_time": time(9, 0),
            "status": "completed",
            "is_paid": True,
            "cost": Decimal("84.00"),
            "base_trip_cost": Decimal("70.00"),
            "regular_vat": Decimal("14.00"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 2,
            "base_driver": secondary_driver or primary_driver,
            "is_guest_driver": False,
            "airport": airport,
            "airport_direction": "to",
            "distance_miles": 15.3,
            "expected_trip_duration_minutes": 47,
            "stop_points": [
                {
                    "point_lat": 51.4995,
                    "point_lng": -0.1749,
                    "point_str": "Knightsbridge Stop",
                }
            ],
        },
        {
            "seed_key": "accepted-guest-driver",
            "passenger": passenger_secondary or passenger_primary,
            "pickup_lat": 51.4700,
            "pickup_lng": -0.4543,
            "pickup_str": "Heathrow Terminal 2",
            "dropoff_lat": 51.5550,
            "dropoff_lng": -0.1084,
            "dropoff_str": "Camden Town",
            "trip_date": now_date + timedelta(days=2),
            "trip_time": time(13, 45),
            "status": "accepted",
            "is_paid": True,
            "cost": Decimal("101.00"),
            "base_trip_cost": Decimal("84.17"),
            "regular_vat": Decimal("16.83"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 3,
            "base_driver": None,
            "is_guest_driver": True,
            "guest_driver_name": "Guest Driver Demo",
            "guest_driver_phone": "+447700900199",
            "guest_driver_company": "Partner Fleet",
            "airport": airport,
            "airport_direction": "from",
            "distance_miles": 22.0,
            "expected_trip_duration_minutes": 63,
            "stop_points": [],
        },
        {
            "seed_key": "cancelled-driver-trip",
            "passenger": passenger_primary,
            "pickup_lat": 51.4975,
            "pickup_lng": -0.1357,
            "pickup_str": "Buckingham Palace Road",
            "dropoff_lat": 51.5099,
            "dropoff_lng": -0.1342,
            "dropoff_str": "Oxford Circus",
            "trip_date": now_date + timedelta(days=3),
            "trip_time": time(8, 20),
            "status": "pending",
            "is_paid": True,
            "cost": Decimal("39.00"),
            "base_trip_cost": Decimal("32.50"),
            "regular_vat": Decimal("6.50"),
            "airport_vat": Decimal("0.00"),
            "min_adjustment": Decimal("0.00"),
            "passengers_count": 1,
            "base_driver": None,
            "is_guest_driver": False,
            "cancelled_by_driver": True,
            "cancelled_by_driver_id": primary_driver or secondary_driver,
            "airport": None,
            "airport_direction": None,
            "distance_miles": 4.2,
            "expected_trip_duration_minutes": 18,
            "stop_points": [],
        },
    )

    created = 0
    for row in samples:
        passenger = row.get("passenger")
        if not passenger:
            continue

        trip, was_created = Trip.objects.get_or_create(
            passenger=passenger,
            pickup_str=row["pickup_str"],
            dropoff_str=row["dropoff_str"],
            trip_date=row["trip_date"],
            trip_time=row["trip_time"],
            defaults={
                "pickup_lat": row["pickup_lat"],
                "pickup_lng": row["pickup_lng"],
                "dropoff_lat": row["dropoff_lat"],
                "dropoff_lng": row["dropoff_lng"],
                "car_type": vehicle_types[0],
                "cost": row["cost"],
                "passengers_count": row["passengers_count"],
                "status": row["status"],
                "is_paid": row.get("is_paid", True),
                "base_trip_cost": row.get("base_trip_cost"),
                "regular_vat": row.get("regular_vat"),
                "airport_vat": row.get("airport_vat"),
                "min_adjustment": row.get("min_adjustment"),
                "base_driver": row.get("base_driver"),
                "is_guest_driver": row.get("is_guest_driver", False),
                "guest_driver_name": row.get("guest_driver_name"),
                "guest_driver_phone": row.get("guest_driver_phone"),
                "guest_driver_company": row.get("guest_driver_company"),
                "cancelled_by_driver": row.get("cancelled_by_driver", False),
                "cancelled_by_driver_id": row.get("cancelled_by_driver_id"),
                "airport": row["airport"],
                "airport_direction": row["airport_direction"],
                "distance_miles": row.get("distance_miles"),
                "expected_trip_duration_minutes": row.get("expected_trip_duration_minutes"),
            },
        )
        if not was_created:
            trip.pickup_lat = row["pickup_lat"]
            trip.pickup_lng = row["pickup_lng"]
            trip.dropoff_lat = row["dropoff_lat"]
            trip.dropoff_lng = row["dropoff_lng"]
            trip.car_type = vehicle_types[0]
            trip.cost = row["cost"]
            trip.passengers_count = row["passengers_count"]
            trip.status = row["status"]
            trip.is_paid = row.get("is_paid", True)
            trip.base_trip_cost = row.get("base_trip_cost")
            trip.regular_vat = row.get("regular_vat")
            trip.airport_vat = row.get("airport_vat")
            trip.min_adjustment = row.get("min_adjustment")
            trip.base_driver = row.get("base_driver")
            trip.is_guest_driver = row.get("is_guest_driver", False)
            trip.guest_driver_name = row.get("guest_driver_name")
            trip.guest_driver_phone = row.get("guest_driver_phone")
            trip.guest_driver_company = row.get("guest_driver_company")
            trip.cancelled_by_driver = row.get("cancelled_by_driver", False)
            trip.cancelled_by_driver_id = row.get("cancelled_by_driver_id")
            trip.airport = row["airport"]
            trip.airport_direction = row["airport_direction"]
            trip.distance_miles = row.get("distance_miles")
            trip.expected_trip_duration_minutes = row.get("expected_trip_duration_minutes")
            trip.save()

        _ensure_trip_stop_points(trip, row.get("stop_points", []))

        if was_created:
            created += 1
        stdout.write(
            f"  Trip sample [{row['seed_key']}]: {trip.pk} "
            f"({trip.status}, {'new' if was_created else 'updated'})"
        )

    stdout.write(style.SUCCESS(f"Sample trips: {len(samples)} ensured, {created} new rows"))
    return created


def run_seed(
    stdout,
    style,
    *,
    dry_run: bool = False,
    with_trips: bool = True,
    with_pricing_command: bool = False,
) -> None:
    """
    Full demo seed: vehicle types → airports → users → driver → optional trips.
    If with_pricing_command, runs the existing ``seed_pricing_data`` management command.
    """
    if dry_run:
        stdout.write(style.WARNING("DRY RUN — rolling back at end"))

    with transaction.atomic():
        seed_vehicle_types(stdout, style, dry_run=dry_run)
        seed_airports(stdout, style, dry_run=dry_run)
        refs = seed_demo_users(stdout, style, dry_run=dry_run)
        seed_demo_normal_drivers(stdout, style, refs.get("driver_users", []), dry_run=dry_run)
        if with_trips:
            seed_sample_trips(stdout, style, dry_run=dry_run)

        if dry_run:
            transaction.set_rollback(True)

    if with_pricing_command and not dry_run:
        from django.core.management import call_command

        stdout.write("Running seed_pricing_data...")
        call_command("seed_pricing_data")

    if not dry_run:
        stdout.write(
            style.SUCCESS(
                f"\nDemo password for all demo users: {DEMO_PASSWORD}\n"
                "Emails: demo.passenger@example.com, demo.passenger2@example.com, "
                "demo.office@example.com, demo.driver@example.com, demo.driver2@example.com"
            )
        )
