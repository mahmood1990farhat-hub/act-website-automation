"""Serialize unified-driver assignments and account/vehicle lifecycle.

The BaseDriver row is the common lock. Read account state AFTER acquiring it.
Legacy drivers retain their behaviour. No payments, email, jobs or n8n calls.
"""
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException
from rest_framework.response import Response

TERMINAL_TRIPS = ("completed", "cancelled", "expired")


class DriverLifecycleConflict(APIException):
    status_code = 409
    default_detail = "Driver availability changed; refresh the operator record."
    default_code = "driver_lifecycle_conflict"


def lock_driver_record(driver_id, using="default"):
    """Caller is in atomic(); common lock order is driver, then profile."""
    from apps.drivers.models import BaseDriver, UnifiedDriverApplication
    driver = get_object_or_404(
        BaseDriver.objects.using(using).select_for_update(), pk=driver_id,
    )
    profile = UnifiedDriverApplication.objects.using(using).select_for_update(
        of=("self",)
    ).filter(onboarding_request__user_id=driver.user_id).first()
    # Separate statement avoids stale joined account snapshots after lock waits.
    driver.user = get_user_model().objects.using(using).get(pk=driver.user_id)
    return driver, profile


def assert_available(driver, profile, car_type_id=None, using="default"):
    from apps.drivers.models import NormalDriver, OperatorVehiclePeriod
    user = driver.user
    if (not user.is_active or not user.is_admin_verified or not user.is_profile_completed
            or not profile.driver_available_from or profile.driver_ceased_available_on
            or profile.vehicle_ceased_available_on):
        raise DriverLifecycleConflict("This unified driver is not available for new assignments.")
    normal = NormalDriver.objects.using(using).select_related("vehicle").filter(driver=driver).first()
    period = OperatorVehiclePeriod.objects.using(using).filter(
        application=profile, ceased_at__isnull=True,
    ).first()
    if not normal or not period or normal.vehicle_id != period.vehicle_id:
        raise DriverLifecycleConflict("The current vehicle does not match its approved operator record.")
    if car_type_id is not None and normal.vehicle.vehicle_type_id != car_type_id:
        raise DriverLifecycleConflict("The verified vehicle class changed; review this assignment again.")
    driver.normal_driver = normal
    return normal, period


@contextmanager
def guard_trip_save(trip, update_fields=None, using="default"):
    """Protect normal ORM assignment/acceptance, including stale API requests.

    Unassigned bookings, terminal transitions and confirmation-only saves are
    unaffected. Bulk assignment writes are unsupported: use existing APIs/save.
    """
    fields = None if update_fields is None else set(update_fields)
    if (not trip.base_driver_id or trip.status in TERMINAL_TRIPS
            or (fields is not None and not fields.intersection({"base_driver", "base_driver_id", "status"}))):
        yield
        return
    from apps.drivers.models import UnifiedDriverApplication
    if not UnifiedDriverApplication.objects.using(using).filter(
        onboarding_request__user__base_driver__id=trip.base_driver_id,
    ).exists():
        yield
        return
    with transaction.atomic(using=using):
        driver, profile = lock_driver_record(trip.base_driver_id, using=using)
        if profile is None:
            raise DriverLifecycleConflict("The unified operator record is unavailable.")
        assert_available(driver, profile, car_type_id=trip.car_type_id, using=using)
        trip.base_driver = driver
        yield


def guard_historical_vehicle_edit(vehicle, update_fields=None, using="default"):
    """Also protect driver self-service edits to previously verified vehicles."""
    if not vehicle.pk:
        return
    from apps.drivers.models import OperatorVehiclePeriod
    from apps.vehicle.models import Vehicle
    if not OperatorVehiclePeriod.objects.using(using).filter(vehicle_id=vehicle.pk).exists():
        return
    names = {"vehicle_number", "make", "model", "color", "year_of_manufacture", "vehicle_type_id", "mot", "phv"}
    if update_fields is not None:
        requested = {"vehicle_type_id" if f == "vehicle_type" else f for f in update_fields}
        names &= requested
    previous = Vehicle.objects.using(using).filter(pk=vehicle.pk).values(*names).first() if names else None
    if previous and any(str(getattr(vehicle, name) or "") != str(previous[name] or "") for name in names):
        raise DriverLifecycleConflict("Use the verified replacement review; historical vehicle records cannot be overwritten.")


def handle_unified_account_action(user_id, action, actor):
    """Temporary suspension is audited, not permanent availability cessation.

    Return None for legacy/pending accounts to preserve their original endpoint.
    Never strand assigned journeys or revive a permanently ceased driver.
    """
    from apps.drivers.models import BaseDriver, UnifiedDriverApplication, OperatorRecordAccessAudit
    from apps.trips.models import Trip
    profile = UnifiedDriverApplication.objects.filter(
        onboarding_request__user_id=user_id, driver_available_from__isnull=False,
    ).first()
    if profile is None:
        return None
    driver_id = BaseDriver.objects.filter(user_id=user_id).values_list("id", flat=True).first()
    if driver_id is None:
        raise DriverLifecycleConflict("Approved operator record has no driver; manual review required.")
    with transaction.atomic():
        driver, profile = lock_driver_record(driver_id)
        user = driver.user
        if profile is None or profile.driver_ceased_available_on:
            raise DriverLifecycleConflict("ACT availability has ended. The account button cannot restore driver approval.")
        active = action == "activate"
        if user.is_active == active:
            return Response({"success": False, "message": "Account already has the requested state."}, status=400)
        if not active and Trip.objects.filter(base_driver=driver).exclude(status__in=TERMINAL_TRIPS).exists():
            raise DriverLifecycleConflict("Complete or formally reassign outstanding trips before suspending this driver.")
        if active:
            user.is_active = True
            assert_available(driver, profile)
        user.is_active = active
        user.save(update_fields=["is_active"])
        OperatorRecordAccessAudit.objects.create(
            application=profile, actor=actor,
            action="account_restored" if active else "account_suspended",
            reason="Temporary account access change; operator availability periods retained.",
        )
        return Response({
            "success": True,
            "message": "Account access restored." if active else "Account suspended; availability history retained.",
            "data": {"user_id": user.pk, "email": user.email, "account_type": user.account_type,
                     "is_active": user.is_active, "full_name": user.get_full_name()},
        })


def should_profile_request(request):
    """Private driver evidence and NI must not be copied into the profiler DB."""
    return not request.path_info.startswith((
        "/api/drivers/", "/api/admin-panel/drivers/", "/api/admin-panel/normal-drivers/",
    ))
