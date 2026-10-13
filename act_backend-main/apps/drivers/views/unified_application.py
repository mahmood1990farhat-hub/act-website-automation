"""Single-submission driver applications and one-time password setup.

New records only. Existing two-stage applications retain their endpoints and
status transitions; this module makes no automation calls or driver approvals.
"""
import hashlib
import logging
import os
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import DriverOnboardingRequest, UnifiedDriverApplication, DriverApplicationDocument
from apps.drivers.models.unified_application import PrivateDriverDocumentStorage
from apps.drivers.serializers.unified_application import (
    APPLICATION_DOCUMENTS,
    UnifiedDriverApplicationSerializer,
    UnifiedVehicleSupplementSerializer,
    private_document_content_type,
    validate_private_driver_document,
)

logger = logging.getLogger(__name__)
User = get_user_model()
GENERIC_RESET_MESSAGE = "If your application is eligible, a new password link will be sent."


def _rate_limited(request, category, window=60):
    # Hash network address rather than store it in a cache key.
    addr = request.META.get("REMOTE_ADDR", "")
    key = "act:driver:unified:" + category + ":" + hashlib.sha256(addr.encode()).hexdigest()
    return not cache.add(key, "1", timeout=window)


def _private_uploads_ready():
    try:
        root = PrivateDriverDocumentStorage().location
        return os.path.isdir(root) and os.access(root, os.W_OK | os.X_OK)
    except (ImproperlyConfigured, ValueError, OSError):
        return False


def _token_pair():
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _email_password_setup(profile_id, raw_token):
    """Run only after database commit, never log secret token or identity."""
    profile = UnifiedDriverApplication.objects.select_related("onboarding_request__user").get(pk=profile_id)
    user = profile.onboarding_request.user
    base = getattr(settings, "ACT_PUBLIC_WEBSITE_URL", "https://airportandcitytransfer.com").rstrip("/")
    link = f"{base}/en/driver-password-setup/#{quote(raw_token, safe='')}"
    try:
        sent = send_mail(
            "ACT Driver Application — Set up your password",
            "Your application has been received and is pending verification.\n\n"
            f"Set your driver portal password within 24 hours:\n{link}\n\n"
            "You will not receive trips until ACT approves your identity and vehicle eligibility.\n"
            "If you did not apply, please contact info@airportandcitytransfer.com.",
            getattr(settings, "DEFAULT_FROM_EMAIL", "info@airportandcitytransfer.com"),
            [user.email],
            fail_silently=False,
        )
        if sent:
            UnifiedDriverApplication.objects.filter(pk=profile_id, welcome_email_sent_at__isnull=True).update(
                welcome_email_sent_at=timezone.now(),
            )
    except Exception:
        logger.warning("ACT driver application welcome email was not sent; recovery resend is available.")


class UnifiedDriverApplicationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post"]

    def post(self, request):
        if _rate_limited(request, "submit", 20):
            return Response({"detail": "Please wait before resubmitting."}, status=429)
        if not _private_uploads_ready():
            return Response({"detail": "Applications are temporarily unavailable. Please contact ACT support."}, status=503)

        serializer = UnifiedDriverApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        email = values["email"]
        if User.objects.filter(email__iexact=email).exists():
            return Response({"email": ["This email is already registered. Sign in or recover your account."]}, status=400)

        uploads = {kind: values.pop(kind) for kind in APPLICATION_DOCUMENTS if kind in values}
        has_vehicle = values["vehicle_ownership"] != "do_not_have_a_phv"
        raw_token, digest = _token_pair()
        saved = []
        storage = PrivateDriverDocumentStorage()
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=None,  # Django sets an unusable password.
                    first_name=values["first_name"],
                    last_name=values["last_name"],
                    phone_number=values["phone_number"],
                    address=values["address"],
                    account_type="normal_driver",
                    is_active=False,
                    is_profile_completed=False,
                    is_admin_verified=False,
                )
                # Legacy required values must not be invented for optional vehicle
                # details or applicant's future availability preferences.
                legacy_vehicle = {
                    "comfort": "5_seater_standard",
                    "comfort_xl": "7_seaters",
                    "executive": "other",
                    "executive_xl": "van_transporter",
                    "first": "other",
                }
                onboarding = DriverOnboardingRequest.objects.create(
                    user=user,
                    full_name=f"{user.first_name} {user.last_name}".strip(),
                    mobile_number=values["phone_number"],
                    email_address=email,
                    home_postcode=values["postcode"],
                    preferred_communication="email",
                    years_experience=values["years_experience"],
                    vehicle_ownership=values["vehicle_ownership"],
                    vehicle_type=legacy_vehicle.get(values.get("vehicle_class_code"), "other"),
                    fuel_type="",
                    availability="",
                    notification_method="email",
                    has_tfl_licence=True,
                    willing_dbs_check=True,
                    agrees_policies=True,
                    status="pending",
                )
                profile = UnifiedDriverApplication.objects.create(
                    onboarding_request=onboarding,
                    date_of_birth=values["date_of_birth"],
                    address=values["address"],
                    postcode=values["postcode"],
                    pco_badge_number=values["pco_badge_number"],
                    pco_badge_expiry=values["pco_badge_expiry"],
                    vehicle_class_code=values.get("vehicle_class_code", ""),
                    vehicle_make=values.get("vehicle_make", ""),
                    vehicle_model=values.get("vehicle_model", ""),
                    vehicle_year=values.get("vehicle_year"),
                    vehicle_registration=values.get("vehicle_registration", ""),
                    vehicle_colour=values.get("vehicle_colour", ""),
                    mot_expiry=values.get("mot_expiry"),
                    insurance_expiry=values.get("insurance_expiry"),
                    accepts_pets=values.get("accepts_pets"),
                    ownership_explanation=values.get("ownership_explanation", ""),
                    awaiting_vehicle=not has_vehicle,
                    passenger_photo_disclosure_consent=values["passenger_photo_disclosure_consent"],
                    setup_token_hash=digest,
                    setup_token_expires_at=timezone.now() + timedelta(hours=24),
                )
                for kind, uploaded in uploads.items():
                    document = DriverApplicationDocument(
                        application=profile,
                        kind=kind,
                        content_type=private_document_content_type(uploaded),
                        original_name=os.path.basename(uploaded.name)[:200],
                        file_size=uploaded.size,
                    )
                    uploaded.seek(0)
                    document.file.save(uploaded.name, uploaded, save=False)
                    saved.append(document.file.name)
                    document.save()
                transaction.on_commit(
                    lambda pk=profile.pk, token=raw_token: _email_password_setup(pk, token),
                    robust=True,
                )
        except IntegrityError:
            for name in saved:
                storage.delete(name)
            return Response({"email": ["An application already exists for these details."]}, status=400)
        except Exception:
            for name in saved:
                storage.delete(name)
            logger.exception("ACT driver application could not be stored.")
            return Response({"detail": "Application could not be saved. Please contact ACT support."}, status=503)

        return Response({
            "success": True,
            "application_id": onboarding.id,
            "status": "awaiting_vehicle" if not has_vehicle else "pending_verification",
            "message": "Application received. Check your email to set a password. Admin verification is required.",
        }, status=status.HTTP_201_CREATED)


class UnifiedDriverVehicleSupplementView(APIView):
    """A pending vehicle-less applicant submits evidence without re-applying.

    Only the owner of an existing unapproved, password-activated unified
    application can add one complete licensed vehicle. This cannot approve,
    verify, assign a trip or replace the private identity evidence.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post"]

    def post(self, request):
        if _rate_limited(request, "vehicle-supplement", 20):
            return Response({"detail": "Please wait before resubmitting."}, status=429)
        if not _private_uploads_ready():
            return Response({"detail": "Private uploads are temporarily unavailable."}, status=503)
        if request.user.account_type != "normal_driver":
            return Response({"detail": "This action is only for pending ACT driver applicants."}, status=403)

        serializer = UnifiedVehicleSupplementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        kinds = ("mot", "insurance", "vehicle_phv", "v5c", "hire_agreement")
        uploads = {kind: payload.pop(kind) for kind in kinds if kind in payload}
        saved_names = []
        storage = PrivateDriverDocumentStorage()
        try:
            with transaction.atomic():
                profile = UnifiedDriverApplication.objects.select_for_update().select_related(
                    "onboarding_request__user"
                ).filter(onboarding_request__user_id=request.user.pk).first()
                if not profile or not profile.awaiting_vehicle:
                    return Response({"detail": "No pending vehicle supplement is required."}, status=409)
                onboarding = profile.onboarding_request
                if (onboarding.status != "pending" or not profile.password_set_at
                        or request.user.is_admin_verified or request.user.is_profile_completed
                        or hasattr(request.user, "base_driver")):
                    return Response({"detail": "This applicant is not eligible to update vehicle evidence."}, status=403)

                for kind, uploaded in uploads.items():
                    document = DriverApplicationDocument(
                        application=profile, kind=kind,
                        content_type=private_document_content_type(uploaded),
                        original_name=os.path.basename(uploaded.name)[:200],
                        file_size=uploaded.size,
                    )
                    uploaded.seek(0)
                    document.file.save(uploaded.name, uploaded, save=False)
                    saved_names.append(document.file.name)
                    document.save()

                for field in (
                    "vehicle_class_code", "vehicle_make", "vehicle_model",
                    "vehicle_year", "vehicle_registration", "vehicle_colour",
                    "mot_expiry", "insurance_expiry", "accepts_pets", "ownership_explanation",
                ):
                    if field in payload:
                        setattr(profile, field, payload[field])
                profile.awaiting_vehicle = False
                profile.save(update_fields=[
                    "vehicle_class_code", "vehicle_make", "vehicle_model", "vehicle_year",
                    "vehicle_registration", "vehicle_colour", "mot_expiry",
                    "insurance_expiry", "accepts_pets", "ownership_explanation",
                    "awaiting_vehicle",
                ])
                onboarding.vehicle_ownership = payload["vehicle_ownership"]
                legacy_map = {
                    "comfort": "5_seater_standard", "comfort_xl": "7_seaters",
                    "executive": "other", "executive_xl": "van_transporter",
                    "first": "other",
                }
                onboarding.vehicle_type = legacy_map.get(payload["vehicle_class_code"], "other")
                onboarding.save(update_fields=["vehicle_ownership", "vehicle_type"])
        except IntegrityError:
            for name in saved_names:
                storage.delete(name)
            return Response({"detail": "Vehicle evidence was already submitted."}, status=409)
        except Exception:
            for name in saved_names:
                storage.delete(name)
            logger.warning("An ACT driver vehicle supplement could not be saved.")
            return Response({"detail": "Unable to save vehicle information. Contact ACT support."}, status=503)

        return Response({
            "success": True,
            "status": "pending_verification",
            "message": "Vehicle evidence received. ACT must still verify the driver and vehicle.",
        })


class UnifiedDriverSetPasswordView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    http_method_names = ["post"]

    def post(self, request):
        if _rate_limited(request, "setup", 10):
            return Response({"detail": "Please wait before retrying."}, status=429)
        raw = request.data.get("token", "")
        password = request.data.get("password", "")
        confirm = request.data.get("confirm_password", "")
        if not isinstance(raw, str) or len(raw) > 160 or len(raw) < 30:
            return Response({"detail": "Invalid or expired password setup link."}, status=400)
        if not isinstance(password, str) or password != confirm or len(password) < 10:
            return Response({"detail": "Password must be at least 10 characters and both entries must match."}, status=400)
        from django.contrib.auth.password_validation import validate_password
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with transaction.atomic():
            profile = UnifiedDriverApplication.objects.select_for_update().select_related("onboarding_request__user").filter(
                setup_token_hash=digest,
                password_set_at__isnull=True,
                setup_token_used_at__isnull=True,
            ).first()
            if not profile or not profile.setup_token_expires_at or profile.setup_token_expires_at <= timezone.now():
                return Response({"detail": "Invalid or expired password setup link."}, status=400)
            user = profile.onboarding_request.user
            try:
                validate_password(password, user=user)
            except Exception:
                return Response({"detail": "Choose a stronger password."}, status=400)
            user.set_password(password)
            # Activate pending portal sign-in, never trip eligibility.
            user.is_active = True
            user.is_admin_verified = False
            user.is_profile_completed = False
            user.save(update_fields=["password", "is_active", "is_admin_verified", "is_profile_completed"])
            now = timezone.now()
            profile.setup_token_hash = ""
            profile.setup_token_used_at = now
            profile.password_set_at = now
            profile.save(update_fields=["setup_token_hash", "setup_token_used_at", "password_set_at"])

        return Response({"success": True, "message": "Password set. Your application remains pending ACT verification."})


class UnifiedDriverResendLinkView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]
    http_method_names = ["post"]

    def post(self, request):
        if _rate_limited(request, "resend", 90):
            return Response({"detail": GENERIC_RESET_MESSAGE})
        email = request.data.get("email", "")
        if isinstance(email, str) and len(email) < 254:
            with transaction.atomic():
                profile = UnifiedDriverApplication.objects.select_for_update().select_related("onboarding_request__user").filter(
                    onboarding_request__user__email__iexact=email.strip(),
                    password_set_at__isnull=True,
                ).first()
                if profile:
                    token, digest = _token_pair()
                    profile.setup_token_hash = digest
                    profile.setup_token_expires_at = timezone.now() + timedelta(hours=24)
                    profile.setup_token_used_at = None
                    profile.welcome_email_sent_at = None
                    profile.save(update_fields=[
                        "setup_token_hash", "setup_token_expires_at",
                        "setup_token_used_at", "welcome_email_sent_at",
                    ])
                    transaction.on_commit(
                        lambda pk=profile.pk, raw=token: _email_password_setup(pk, raw),
                        robust=True,
                    )
        return Response({"detail": GENERIC_RESET_MESSAGE})


class UnifiedDriverCorrectionView(APIView):
    """Applicant-only replacement of EXACT fields requested by an ACT admin.

    Original identity documents remain private. The database changes only after
    all requested values/documents validate, with old files deleted on commit.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["post"]

    def post(self, request):
        if _rate_limited(request, "corrections", 20):
            return Response({"detail": "Please wait before resubmitting."}, status=429)
        if not _private_uploads_ready():
            return Response({"detail": "Private uploads are temporarily unavailable."}, status=503)
        if request.user.account_type != "normal_driver":
            return Response({"detail": "This is only for ACT driver applicants."}, status=403)

        from datetime import date
        from apps.drivers.views.unified_admin import PROFILE_CORRECTION_FIELDS
        doc_kinds = {key for key, _ in DriverApplicationDocument.KINDS}
        stored = []
        displaced = []
        storage = PrivateDriverDocumentStorage()
        try:
            with transaction.atomic():
                profile = UnifiedDriverApplication.objects.select_for_update().select_related(
                    "onboarding_request__user"
                ).filter(onboarding_request__user_id=request.user.pk).first()
                if not profile:
                    return Response({"detail": "No unified driver application exists."}, status=404)
                onboarding = profile.onboarding_request
                if (onboarding.status != "needs_modification" or
                        not profile.password_set_at or
                        request.user.is_admin_verified or
                        request.user.is_profile_completed or
                        hasattr(request.user, "base_driver")):
                    return Response({"detail": "Corrections are not authorized for this account."}, status=403)

                requested = set(onboarding.files_need_modification or [])
                if not requested or not requested.issubset(doc_kinds | PROFILE_CORRECTION_FIELDS):
                    return Response({"detail": "Invalid admin correction request; contact ACT support."}, status=409)
                submitted = set(request.data.keys())
                if submitted != requested:
                    return Response({
                        "detail": "Submit every requested field only.",
                        "missing": sorted(requested - submitted),
                        "unexpected": sorted(submitted - requested),
                    }, status=400)

                amended_fields = []
                for field in sorted(requested & PROFILE_CORRECTION_FIELDS):
                    raw = request.data.get(field)
                    if not isinstance(raw, str) or not raw.strip():
                        return Response({field: "This corrected value is required."}, status=400)
                    raw = raw.strip()
                    value = raw
                    if field.endswith("_expiry"):
                        try:
                            value = date.fromisoformat(raw)
                        except ValueError:
                            return Response({field: "Use YYYY-MM-DD."}, status=400)
                        if value <= date.today():
                            return Response({field: "Expiry must be in the future."}, status=400)
                    elif field == "vehicle_year":
                        try:
                            value = int(raw)
                        except ValueError:
                            return Response({field: "Enter a valid vehicle year."}, status=400)
                        if value < 2015 or value > date.today().year:
                            return Response({field: "Vehicle year must be 2015–present."}, status=400)
                    else:
                        max_length = profile._meta.get_field(field).max_length
                        if len(raw) > max_length:
                            return Response({field: "Value is too long."}, status=400)
                    setattr(profile, field, value)
                    amended_fields.append(field)

                for kind in sorted(requested & doc_kinds):
                    upload = request.FILES.get(kind)
                    if upload is None:
                        return Response({kind: "A replacement document is required."}, status=400)
                    validate_private_driver_document(kind, upload)
                    old = profile.documents.filter(kind=kind).first()
                    if old:
                        displaced.append(old.file.name)
                        doc = old
                    else:
                        doc = DriverApplicationDocument(application=profile, kind=kind)
                    doc.content_type = private_document_content_type(upload)
                    doc.original_name = os.path.basename(upload.name)[:200]
                    doc.file_size = upload.size
                    upload.seek(0)
                    doc.file.save(upload.name, upload, save=False)
                    stored.append(doc.file.name)
                    doc.save()

                if amended_fields:
                    profile.save(update_fields=amended_fields)
                onboarding.status = "pending"
                onboarding.files_need_modification = []
                onboarding.save(update_fields=["status", "files_need_modification"])
                # Old private files are removed only after the new rows commit.
                for old_name in displaced:
                    transaction.on_commit(
                        lambda name=old_name: storage.delete(name), robust=True,
                    )
        except serializers.ValidationError as exc:
            for name in stored:
                storage.delete(name)
            return Response(exc.detail, status=400)
        except Exception:
            for name in stored:
                storage.delete(name)
            logger.warning("ACT driver requested corrections could not be saved.")
            return Response({"detail": "Corrections could not be saved. Contact ACT support."}, status=503)
        return Response({
            "success": True, "status": "pending_verification",
            "message": "Your corrections have been received for ACT admin re-review.",
        })


class PrivateDriverApplicationDocumentView(APIView):
    """Only authorized admins can access evidence; no public URLs or base64."""
    permission_classes = [IsAdminUser]
    http_method_names = ["get"]

    def get(self, request, document_id):
        document = get_object_or_404(
            DriverApplicationDocument.objects.select_related("application__onboarding_request"),
            pk=document_id,
        )
        response = FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.original_name or "act-driver-document",
            content_type=document.content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
