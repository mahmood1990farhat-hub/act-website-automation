"""Admin-only unified applicant evidence review and final approval.

The existing legacy step1/step2 admin review routes remain intact.
"""
import logging
import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import (
    BaseDriver, NormalDriver, DriverOnboardingRequest, UnifiedDriverApplication,
    DriverApplicationDocument,
)
from apps.vehicle.models import Vehicle, VehicleType

logger = logging.getLogger(__name__)
IDENTITY_DOCS = {"pco_front", "pco_back", "dvla_front", "dvla_back", "driver_photo"}


PROFILE_CORRECTION_FIELDS = {
    "pco_badge_number", "pco_badge_expiry",
    "mot_expiry", "insurance_expiry", "vehicle_registration",
    "vehicle_colour", "vehicle_make", "vehicle_model", "vehicle_year",
}
CORRECTION_KINDS = {key for key, _ in DriverApplicationDocument.KINDS} | PROFILE_CORRECTION_FIELDS


def _notify_changes(profile_id):
    profile = UnifiedDriverApplication.objects.select_related(
        "onboarding_request__user"
    ).get(pk=profile_id)
    try:
        send_mail(
            "ACT Driver Application — Corrections required",
            "ACT needs corrected information before we can finish reviewing "
            "your driver application. Sign in to the ACT driver application "
            "status page, review the request and upload only the requested "
            "evidence. Your account is not approved for trips.",
            getattr(settings, "DEFAULT_FROM_EMAIL", "info@airportandcitytransfer.com"),
            [profile.onboarding_request.user.email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("ACT driver correction email failed; admin follow-up required.")


def _expected_document_kinds(profile):
    required = set(IDENTITY_DOCS)
    if not profile.awaiting_vehicle:
        required.update(("mot", "insurance", "vehicle_phv"))
        ownership = profile.onboarding_request.vehicle_ownership
        if ownership == "phv_owner":
            required.add("v5c")
        elif ownership == "hiring_a_phv":
            required.add("hire_agreement")
        elif ownership == "other":
            # Specific ownership/right-of-use proof required, validated again
            # below as v5c OR hire_agreement.
            pass
    return required


def _notify_review(profile_id, approved):
    profile = UnifiedDriverApplication.objects.select_related("onboarding_request__user").get(pk=profile_id)
    user = profile.onboarding_request.user
    message = (
        "Your ACT driver application has passed verification. You can now use your "
        "approved driver account to review eligible trip offers."
        if approved else
        "Your ACT driver application could not be approved. Please contact "
        "info@airportandcitytransfer.com for next steps."
    )
    try:
        send_mail(
            "ACT Driver Application — Review result",
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", "info@airportandcitytransfer.com"),
            [user.email],
            fail_silently=False,
        )
    except Exception:
        logger.warning("Unified driver final-review notification failed; admin follow-up is needed.")


class AdminUnifiedApplicationDetailView(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ["get"]

    def get(self, request, request_id):
        profile = get_object_or_404(
            UnifiedDriverApplication.objects.select_related("onboarding_request__user").prefetch_related("documents"),
            onboarding_request_id=request_id,
        )
        onboarding = profile.onboarding_request
        user = onboarding.user
        return Response({
            "application_id": onboarding.pk,
            "status": onboarding.status,
            "awaiting_vehicle": profile.awaiting_vehicle,
            "password_is_set": bool(profile.password_set_at),
            "personal": {
                "first_name": user.first_name, "last_name": user.last_name,
                "email": user.email, "phone_number": user.phone_number,
                "address": profile.address, "postcode": profile.postcode,
                "date_of_birth": profile.date_of_birth,
            },
            "licence": {
                "number": profile.pco_badge_number,
                "expiry": profile.pco_badge_expiry,
                "years_experience": onboarding.years_experience,
            },
            "vehicle": {
                "ownership": onboarding.vehicle_ownership,
                "class_code": profile.vehicle_class_code,
                "make": profile.vehicle_make,
                "model": profile.vehicle_model,
                "year": profile.vehicle_year,
                "registration": profile.vehicle_registration,
                "colour": profile.vehicle_colour,
                "mot_expiry": profile.mot_expiry,
                "insurance_expiry": profile.insurance_expiry,
                "accepts_pets": profile.accepts_pets,
                "explanation": profile.ownership_explanation,
            },
            "documents": [
                {
                    "id": doc.pk, "kind": doc.kind, "name": doc.original_name,
                    "size": doc.file_size,
                    # Always access through an admin-authenticated download.
                    "download_endpoint": f"/api/drivers/admin/unified-documents/{doc.pk}/",
                }
                for doc in profile.documents.all()
            ],
        })


class AdminUnifiedApplicationDecisionView(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ["post"]

    def post(self, request, request_id):
        action = request.data.get("action")
        if action not in ("approve", "reject", "request_changes"):
            return Response({"detail": "Choose approve, reject or request corrections."}, status=400)

        published_photo = None
        try:
            with transaction.atomic():
                profile = get_object_or_404(
                    UnifiedDriverApplication.objects.select_for_update().select_related("onboarding_request__user"),
                    onboarding_request_id=request_id,
                )
                onboarding = profile.onboarding_request
                user = onboarding.user
                if onboarding.status != "pending":
                    return Response({"detail": "Application has already been reviewed or is on hold."}, status=400)
                now = timezone.now()

                if action == "reject":
                    reason = str(request.data.get("reason", "")).strip()
                    if len(reason) < 8:
                        return Response({"reason": "Give a reason for rejection."}, status=400)
                    onboarding.status = "final_rejected"
                    onboarding.rejection_reason = reason
                    onboarding.reviewed_by = request.user
                    onboarding.reviewed_at = now
                    onboarding.save(update_fields=[
                        "status", "rejection_reason", "reviewed_by", "reviewed_at",
                    ])
                    profile.reviewed_at = now
                    profile.save(update_fields=["reviewed_at"])
                    transaction.on_commit(
                        lambda pk=profile.pk: _notify_review(pk, False), robust=True,
                    )
                    return Response({"success": True, "status": "final_rejected"})

                if action == "request_changes":
                    reason = str(request.data.get("reason", "")).strip()
                    fields = request.data.get("files_to_modify", [])
                    if len(reason) < 8:
                        return Response({"reason": "Give a clear correction reason."}, status=400)
                    if (not isinstance(fields, list) or not fields or len(fields) > 16
                            or any(not isinstance(key, str) or key not in CORRECTION_KINDS for key in fields)
                            or len(set(fields)) != len(fields)):
                        return Response({"files_to_modify": "Select specific valid document or detail fields."}, status=400)
                    onboarding.status = "needs_modification"
                    onboarding.files_need_modification = fields
                    onboarding.rejection_reason = reason
                    onboarding.reviewed_by = request.user
                    onboarding.reviewed_at = now
                    onboarding.save(update_fields=[
                        "status", "files_need_modification", "rejection_reason",
                        "reviewed_by", "reviewed_at",
                    ])
                    profile.reviewed_at = now
                    profile.save(update_fields=["reviewed_at"])
                    transaction.on_commit(
                        lambda pk=profile.pk: _notify_changes(pk), robust=True,
                    )
                    return Response({
                        "success": True, "status": "needs_modification",
                        "files_to_modify": fields,
                    })

                if profile.awaiting_vehicle:
                    return Response({"detail": "Driver has no verified vehicle. Approval for trip work is prohibited."}, status=400)
                if not profile.password_set_at or not user.is_active:
                    return Response({"detail": "Applicant must activate the password first."}, status=400)
                if not request.data.get("documents_reviewed") is True:
                    return Response({"documents_reviewed": "Confirm inspection of every required identity and vehicle document."}, status=400)
                if not request.data.get("dbs_cleared") is True:
                    return Response({"dbs_cleared": "Confirm valid DBS clearance before approval."}, status=400)
                if not profile.passenger_photo_disclosure_consent:
                    return Response({"passenger_photo_disclosure_consent": "Applicant has not accepted passenger-facing driver photo disclosure."}, status=400)
                if request.data.get("photo_disclosure_consent") is not True:
                    return Response({"photo_disclosure_consent": "Confirm inspection of the applicant's photo disclosure consent."}, status=400)
                today = date.today()
                if profile.pco_badge_expiry <= today or not profile.mot_expiry or profile.mot_expiry <= today or not profile.insurance_expiry or profile.insurance_expiry <= today:
                    return Response({"detail": "One or more required licences/certificates are expired."}, status=400)
                by_kind = {doc.kind: doc for doc in profile.documents.all()}
                missing = sorted(_expected_document_kinds(profile) - set(by_kind))
                ownership = onboarding.vehicle_ownership
                if ownership == "other" and not ({"v5c", "hire_agreement"} & set(by_kind)):
                    missing.append("v5c or hire_agreement")
                if missing:
                    return Response({"documents": "Missing verified private evidence: " + ", ".join(missing)}, status=400)
                if hasattr(user, "base_driver"):
                    return Response({"detail": "Driver already exists; duplicate onboarding is not permitted."}, status=400)
                vehicle_type = VehicleType.objects.filter(code=profile.vehicle_class_code).first()
                if not vehicle_type:
                    return Response({"vehicle_class_code": "Vehicle class is no longer available."}, status=400)

                # The original regulated documents remain ONLY in private storage.
                # Public BaseDriver/Vehicle legacy document fields are left empty;
                # admin reviews real evidence through the private download route.
                vehicle = Vehicle.objects.create(
                    vehicle_number=profile.vehicle_registration,
                    make=profile.vehicle_make,
                    model=profile.vehicle_model,
                    color=profile.vehicle_colour,
                    year_of_manufacture=profile.vehicle_year,
                    vehicle_type=vehicle_type,
                    mot="", phv="",
                )
                base = BaseDriver.objects.create(
                    user=user, pco="", dbs="", dvla="",
                    pco_licence_number=profile.pco_badge_number,
                )
                NormalDriver.objects.create(driver=base, vehicle=vehicle)

                # Only the approved customer-facing driver photo is published.
                # Never publish DVLA/badge/V5C/insurance documents.
                original = by_kind["driver_photo"]
                ext = ".png" if original.content_type == "image/png" else ".jpg"
                with original.file.open("rb") as source:
                    base.driver_photo.save(
                        f"{uuid.uuid4().hex}{ext}", ContentFile(source.read()), save=True,
                    )
                published_photo = base.driver_photo.name

                user.is_admin_verified = True
                user.is_profile_completed = True
                user.save(update_fields=["is_admin_verified", "is_profile_completed"])
                onboarding.status = "final_approved"
                onboarding.reviewed_by = request.user
                onboarding.reviewed_at = now
                onboarding.save(update_fields=["status", "reviewed_by", "reviewed_at"])
                profile.reviewed_at = now
                profile.save(update_fields=["reviewed_at"])
                transaction.on_commit(
                    lambda pk=profile.pk: _notify_review(pk, True), robust=True,
                )
                return Response({
                    "success": True, "status": "final_approved",
                    "driver_id": base.pk, "vehicle_id": vehicle.pk,
                }, status=status.HTTP_200_OK)
        except Exception:
            if published_photo:
                from django.core.files.storage import default_storage
                default_storage.delete(published_photo)
            logger.exception("Unified driver review could not be completed.")
            return Response({"detail": "Review could not be completed. Please contact ACT support."}, status=503)
