"""Restricted ACT operator register lifecycle for newly approved unified drivers.

Legacy drivers and all booking/payment/dispatch operations are left untouched.
Vehicle originals belong to separate private historical periods.
"""
import logging
import os

from cryptography.fernet import InvalidToken
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import (
    BaseDriver, NormalDriver, UnifiedDriverApplication,
    OperatorVehiclePeriod, OperatorVehicleEvidence, OperatorRecordAccessAudit,
)
from apps.drivers.models.unified_application import PrivateDriverDocumentStorage
from apps.drivers.operator_records import decrypt_operator_ni
from apps.drivers.operational_safety import lock_driver_record
from apps.drivers.serializers.unified_application import (
    UnifiedVehicleSupplementSerializer, private_document_content_type,
)
from apps.drivers.views.unified_application import _private_uploads_ready
from apps.trips.models import Trip
from apps.vehicle.models import Vehicle, VehicleType

logger = logging.getLogger(__name__)
VEHICLE_DOCS = ("mot", "insurance", "vehicle_phv", "v5c", "hire_agreement")
TRIP_TERMINAL_STATUSES = ("completed", "cancelled", "expired")


def _outstanding_assignment(base_driver):
    """Do not silently cancel or transfer any assigned unfinished booking."""
    return Trip.objects.filter(base_driver=base_driver).exclude(
        status__in=TRIP_TERMINAL_STATUSES,
    ).exists()


def _active_record(request_id, allow_suspended=False):
    """Share the assignment lock BEFORE reading profile/account/vehicle state."""
    initial = get_object_or_404(UnifiedDriverApplication, onboarding_request_id=request_id)
    driver_id = BaseDriver.objects.filter(
        user_id=initial.onboarding_request.user_id,
    ).values_list("id", flat=True).first()
    if driver_id is None:
        return initial, None, None, "Driver vehicle/operator records differ; manual review required."
    driver, profile = lock_driver_record(driver_id)
    if profile is None or profile.pk != initial.pk:
        return initial, None, None, "Operator record changed; refresh the application."
    user = driver.user
    profile.onboarding_request.user = user
    if (profile.onboarding_request.status != "final_approved"
            or not profile.driver_available_from
            or profile.driver_ceased_available_on is not None
            or (not user.is_active and not allow_suspended)
            or not user.is_admin_verified or not user.is_profile_completed):
        return profile, None, None, "Driver is not currently available for ACT work."
    normal = NormalDriver.objects.select_for_update().filter(driver=driver).first()
    period = OperatorVehiclePeriod.objects.select_for_update().filter(
        application=profile, ceased_at__isnull=True,
    ).first()
    if not normal or not period or period.vehicle_id != normal.vehicle_id:
        return profile, None, None, "Driver vehicle/operator records differ; manual review required."
    return profile, normal, period, None


class OperatorVehicleReplacementSerializer(UnifiedVehicleSupplementSerializer):
    """The same genuine-document checks as the existing no-vehicle supplement."""

    registered_keeper_name = serializers.CharField(max_length=150)
    registered_keeper_address = serializers.CharField(max_length=500)
    replacement_reason = serializers.CharField(min_length=8, max_length=450)
    documents_reviewed = serializers.BooleanField()
    operator_records_checked = serializers.BooleanField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("documents_reviewed") or not attrs.get("operator_records_checked"):
            raise serializers.ValidationError({
                "documents_reviewed": "ACT must verify vehicle evidence and registered keeper details.",
            })
        return attrs


class AdminUnifiedVehicleReplaceView(APIView):
    """Preserve the original vehicle/keeper snapshot and all private evidence."""

    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post"]

    def post(self, request, request_id):
        if not _private_uploads_ready():
            return Response({"detail": "Private vehicle document storage is unavailable."}, status=503)
        serializer = OperatorVehicleReplacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        documents = {kind: payload.pop(kind) for kind in VEHICLE_DOCS if kind in payload}
        saved = []
        try:
            with transaction.atomic():
                profile, normal, previous, problem = _active_record(request_id)
                if problem:
                    return Response({"detail": problem}, status=409)
                if _outstanding_assignment(normal.driver):
                    return Response({
                        "detail": "Complete or formally reassign outstanding trips before changing this vehicle."
                    }, status=409)
                vehicle_type = VehicleType.objects.filter(code=payload["vehicle_class_code"]).first()
                if not vehicle_type:
                    return Response({"vehicle_class_code": "Vehicle class is not registered."}, status=400)

                now = timezone.now()
                new_vehicle = Vehicle.objects.create(
                    vehicle_number=payload["vehicle_registration"],
                    make=payload["vehicle_make"],
                    model=payload["vehicle_model"],
                    color=payload["vehicle_colour"],
                    year_of_manufacture=payload["vehicle_year"],
                    vehicle_type=vehicle_type,
                    mot="", phv="",
                )
                previous.ceased_at = now
                previous.close_reason = payload["replacement_reason"]
                previous.closed_by = request.user
                previous.save(update_fields=["ceased_at", "close_reason", "closed_by"])

                period = OperatorVehiclePeriod.objects.create(
                    application=profile,
                    vehicle=new_vehicle,
                    vehicle_registration=new_vehicle.vehicle_number,
                    vehicle_make=new_vehicle.make,
                    vehicle_model=new_vehicle.model,
                    vehicle_colour=new_vehicle.color,
                    vehicle_year=new_vehicle.year_of_manufacture,
                    vehicle_class_code=payload["vehicle_class_code"],
                    ownership=payload["vehicle_ownership"],
                    registered_keeper_name=payload["registered_keeper_name"],
                    registered_keeper_address=payload["registered_keeper_address"],
                    available_from=now,
                    reviewed_by=request.user,
                )
                for kind, uploaded in documents.items():
                    evidence = OperatorVehicleEvidence(
                        period=period,
                        kind=kind,
                        original_name=os.path.basename(uploaded.name)[:200],
                        content_type=private_document_content_type(uploaded),
                        file_size=uploaded.size,
                    )
                    uploaded.seek(0)
                    evidence.file.save(uploaded.name, uploaded, save=False)
                    saved.append(evidence.file.name)
                    evidence.save()

                normal.vehicle = new_vehicle
                normal.save(update_fields=["vehicle"])
                profile.vehicle_class_code = payload["vehicle_class_code"]
                profile.vehicle_make = payload["vehicle_make"]
                profile.vehicle_model = payload["vehicle_model"]
                profile.vehicle_year = payload["vehicle_year"]
                profile.vehicle_registration = payload["vehicle_registration"]
                profile.vehicle_colour = payload["vehicle_colour"]
                profile.mot_expiry = payload["mot_expiry"]
                profile.insurance_expiry = payload["insurance_expiry"]
                profile.accepts_pets = payload["accepts_pets"]
                profile.ownership_explanation = payload.get("ownership_explanation", "")
                profile.registered_keeper_name = payload["registered_keeper_name"]
                profile.registered_keeper_address = payload["registered_keeper_address"]
                profile.vehicle_available_from = timezone.localdate()
                profile.vehicle_ceased_available_on = None
                profile.operator_record_verified_at = now
                profile.save(update_fields=[
                    "vehicle_class_code", "vehicle_make", "vehicle_model",
                    "vehicle_year", "vehicle_registration", "vehicle_colour",
                    "mot_expiry", "insurance_expiry", "accepts_pets",
                    "ownership_explanation", "registered_keeper_name",
                    "registered_keeper_address", "vehicle_available_from",
                    "vehicle_ceased_available_on", "operator_record_verified_at",
                ])
                onboarding = profile.onboarding_request
                onboarding.vehicle_ownership = payload["vehicle_ownership"]
                class_map = {
                    "comfort": "5_seater_standard",
                    "comfort_xl": "7_seaters",
                    "executive": "other",
                    "executive_xl": "van_transporter",
                    "first_class": "other",
                }
                onboarding.vehicle_type = class_map.get(payload["vehicle_class_code"], "other")
                onboarding.save(update_fields=["vehicle_ownership", "vehicle_type"])
                OperatorRecordAccessAudit.objects.create(
                    application=profile, actor=request.user,
                    action="vehicle_replaced", reason=payload["replacement_reason"],
                )
                return Response({
                    "success": True, "status": "vehicle_replaced",
                    "vehicle_period_id": period.pk,
                }, status=200)
        except Exception:
            private_storage = PrivateDriverDocumentStorage()
            for name in saved:
                try:
                    private_storage.delete(name)
                except (ValueError, OSError):
                    pass
            logger.warning("ACT admin vehicle replacement failed; no details logged.")
            return Response({"detail": "Vehicle replacement could not be completed."}, status=503)


class AdminUnifiedDriverCeaseView(APIView):
    """End this driver's availability; never touch assigned trips or delete records."""

    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser]
    http_method_names = ["post"]

    def post(self, request, request_id):
        reason = request.data.get("reason", "")
        if (not isinstance(reason, str) or not 8 <= len(reason.strip()) <= 450
                or request.data.get("confirmed_no_outstanding_trips") is not True):
            return Response({"detail": "Provide a reason and confirm assignment review."}, status=400)

        with transaction.atomic():
            profile, normal, period, problem = _active_record(request_id, allow_suspended=True)
            if problem:
                return Response({"detail": problem}, status=409)
            if _outstanding_assignment(normal.driver):
                return Response({
                    "detail": "Outstanding trips must be completed or reassigned before ending availability."
                }, status=409)

            now = timezone.now()
            period.ceased_at = now
            period.close_reason = ("Driver ceased ACT availability: " + reason.strip())[:500]
            period.closed_by = request.user
            period.save(update_fields=["ceased_at", "close_reason", "closed_by"])
            profile.driver_ceased_available_on = timezone.localdate()
            profile.vehicle_ceased_available_on = timezone.localdate()
            profile.save(update_fields=["driver_ceased_available_on", "vehicle_ceased_available_on"])
            user = profile.onboarding_request.user
            user.is_admin_verified = False
            user.is_profile_completed = False
            user.save(update_fields=["is_admin_verified", "is_profile_completed"])
            OperatorRecordAccessAudit.objects.create(
                application=profile, actor=request.user,
                action="availability_ceased", reason=reason.strip(),
            )
        return Response({"success": True, "status": "ceased", "trip_actions": "none"}, status=200)


class AdminUnifiedVehicleEvidenceView(APIView):
    """Authorized admin can stream historical vehicle evidence, never a public URL."""

    permission_classes = [IsAdminUser]
    http_method_names = ["get"]

    def get(self, request, document_id):
        evidence = get_object_or_404(OperatorVehicleEvidence, pk=document_id)
        response = FileResponse(
            evidence.file.open("rb"), as_attachment=True,
            filename=evidence.original_name or "ACT-vehicle-evidence",
            content_type=evidence.content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AdminOperatorNIInspectionView(APIView):
    """Audited superuser-only NI readback for legitimate TfL inspection."""

    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser]
    http_method_names = ["post"]

    def post(self, request, request_id):
        if not request.user.is_superuser:
            return Response({"detail": "Additional ACT operator authority is required."}, status=403)
        reason = request.data.get("reason", "")
        if not isinstance(reason, str) or not 8 <= len(reason.strip()) <= 450:
            return Response({"detail": "Enter a legitimate inspection reason."}, status=400)
        profile = get_object_or_404(
            UnifiedDriverApplication, onboarding_request_id=request_id,
        )
        if not profile.national_insurance_ciphertext:
            return Response({"detail": "No NI record is available."}, status=404)
        try:
            ni = decrypt_operator_ni(profile.national_insurance_ciphertext)
        except (ImproperlyConfigured, InvalidToken, ValueError):
            return Response({"detail": "Secure operator register access unavailable."}, status=503)
        with transaction.atomic():
            OperatorRecordAccessAudit.objects.create(
                application=profile, actor=request.user,
                action="ni_inspection", reason=reason.strip(),
            )
        response = Response({"national_insurance_number": ni}, status=200)
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response
