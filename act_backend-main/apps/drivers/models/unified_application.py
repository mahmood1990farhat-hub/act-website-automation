"""One-shot applications, linked to existing onboarding rather than replacing it.

Original identity and licence documents use a separate private storage root.
They are NEVER stored in public MEDIA_ROOT or exposed through FieldFile.url.
"""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDriverDocumentStorage(FileSystemStorage):
    """Dynamic private storage allows isolated test overrides, no public URL."""

    def __init__(self):
        super().__init__(location=None, base_url=None)

    @property
    def location(self):
        root = getattr(settings, "ACT_DRIVER_PRIVATE_UPLOAD_ROOT", "")
        if not root:
            raise ImproperlyConfigured("ACT_DRIVER_PRIVATE_UPLOAD_ROOT is required for unified applications")
        # Resolve symlinks as well as ../ segments. A private-looking path
        # linking into an Nginx-served media/static directory is NOT private.
        root = os.path.realpath(os.path.abspath(str(root)))
        prohibited_roots = (settings.MEDIA_ROOT, getattr(settings, "STATIC_ROOT", None))
        for exposed in prohibited_roots:
            if not exposed:
                continue
            public = os.path.realpath(os.path.abspath(str(exposed)))
            if os.path.commonpath([root, public]) == public:
                raise ImproperlyConfigured("Driver evidence storage cannot be inside a public media/static root")
        return root

    @property
    def base_url(self):
        return None

    @property
    def file_permissions_mode(self):
        return 0o600

    @property
    def directory_permissions_mode(self):
        return 0o700

    def url(self, name):
        raise ValueError("Private driver documents have no public URL")


def private_driver_upload_path(document, filename):
    # Do not incorporate applicant names, licence IDs or submitted filenames.
    return f"applications/{document.application_id}/{uuid.uuid4().hex}"


class UnifiedDriverApplication(models.Model):
    """Optional profile for a new unified application; legacy rows have none."""

    onboarding_request = models.OneToOneField(
        "drivers.DriverOnboardingRequest",
        on_delete=models.PROTECT,
        related_name="unified_application",
    )
    date_of_birth = models.DateField()
    address = models.CharField(max_length=255)
    postcode = models.CharField(max_length=20)
    pco_badge_number = models.CharField(max_length=50)
    pco_badge_expiry = models.DateField()
    vehicle_class_code = models.CharField(max_length=32, blank=True, default="")
    vehicle_make = models.CharField(max_length=80, blank=True, default="")
    vehicle_model = models.CharField(max_length=80, blank=True, default="")
    vehicle_year = models.PositiveSmallIntegerField(null=True, blank=True)
    vehicle_registration = models.CharField(max_length=50, blank=True, default="")
    vehicle_colour = models.CharField(max_length=50, blank=True, default="")
    mot_expiry = models.DateField(null=True, blank=True)
    insurance_expiry = models.DateField(null=True, blank=True)
    accepts_pets = models.BooleanField(null=True, blank=True)
    ownership_explanation = models.CharField(max_length=500, blank=True, default="")
    awaiting_vehicle = models.BooleanField(default=False)
    passenger_photo_disclosure_consent = models.BooleanField(default=False)
    # Restricted TfL operator records for newly approved unified applicants.
    # NI is encrypted; driver and vehicle periods are independent.
    national_insurance_ciphertext = models.CharField(max_length=255, blank=True, default="")
    registered_keeper_name = models.CharField(max_length=150, blank=True, default="")
    registered_keeper_address = models.CharField(max_length=500, blank=True, default="")
    driver_available_from = models.DateField(null=True, blank=True)
    driver_ceased_available_on = models.DateField(null=True, blank=True)
    vehicle_available_from = models.DateField(null=True, blank=True)
    vehicle_ceased_available_on = models.DateField(null=True, blank=True)
    operator_record_verified_at = models.DateTimeField(null=True, blank=True)
    setup_token_hash = models.CharField(max_length=64, blank=True, default="")
    setup_token_expires_at = models.DateTimeField(null=True, blank=True)
    setup_token_used_at = models.DateTimeField(null=True, blank=True)
    welcome_email_sent_at = models.DateTimeField(null=True, blank=True)
    password_set_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Unified driver application #{self.onboarding_request_id}"


class DriverApplicationDocument(models.Model):
    """Private, individually downloadable evidence with predictable kinds only."""

    KINDS = (
        ("pco_front", "TfL badge front"),
        ("pco_back", "TfL badge back"),
        ("dvla_front", "DVLA licence front"),
        ("dvla_back", "DVLA licence back"),
        ("driver_photo", "Driver profile photograph"),
        ("mot", "MOT certificate"),
        ("insurance", "Vehicle insurance"),
        ("v5c", "V5C logbook"),
        ("vehicle_phv", "Vehicle PHV licence"),
        ("hire_agreement", "Hired vehicle proof"),
        ("dbs", "DBS certificate"),
    )
    application = models.ForeignKey(
        UnifiedDriverApplication, on_delete=models.CASCADE, related_name="documents",
    )
    kind = models.CharField(max_length=25, choices=KINDS)
    file = models.FileField(
        storage=PrivateDriverDocumentStorage(), upload_to=private_driver_upload_path,
        max_length=260,
    )
    content_type = models.CharField(max_length=60)
    original_name = models.CharField(max_length=200, blank=True)
    file_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("application", "kind"), name="unique_driver_application_document_kind"),
        ]

    def __str__(self):
        return f"Driver evidence #{self.application_id}: {self.kind}"


def private_operator_vehicle_evidence_path(document, filename):
    """Private evidence per vehicle period; never expose licence numbers/filenames."""
    return f"operator-vehicles/{document.period_id}/{uuid.uuid4().hex}"


class OperatorVehiclePeriod(models.Model):
    """Historical vehicle and keeper snapshot; close an old period, never rewrite it."""

    application = models.ForeignKey(
        UnifiedDriverApplication, on_delete=models.PROTECT, related_name="operator_vehicle_periods",
    )
    vehicle = models.ForeignKey("vehicle.Vehicle", on_delete=models.PROTECT, related_name="+")
    vehicle_registration = models.CharField(max_length=50)
    vehicle_make = models.CharField(max_length=80)
    vehicle_model = models.CharField(max_length=80)
    vehicle_colour = models.CharField(max_length=50)
    vehicle_class_code = models.CharField(max_length=32)
    vehicle_year = models.PositiveSmallIntegerField()
    ownership = models.CharField(max_length=20)
    registered_keeper_name = models.CharField(max_length=150)
    registered_keeper_address = models.CharField(max_length=500)
    available_from = models.DateTimeField()
    ceased_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.CharField(max_length=500, blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True, blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("application",), condition=models.Q(ceased_at__isnull=True),
                name="unique_active_unified_vehicle_period",
            ),
        ]
        ordering = ["-available_from", "-id"]


class OperatorVehicleEvidence(models.Model):
    """New private evidence attached to the exact replacement vehicle period."""

    KINDS = (
        ("mot", "MOT certificate"), ("insurance", "Insurance certificate"),
        ("vehicle_phv", "PHV vehicle licence"), ("v5c", "V5C logbook"),
        ("hire_agreement", "Proof of lawful hire"),
    )
    period = models.ForeignKey(
        OperatorVehiclePeriod, on_delete=models.PROTECT, related_name="evidence",
    )
    kind = models.CharField(max_length=25, choices=KINDS)
    file = models.FileField(
        storage=PrivateDriverDocumentStorage(), upload_to=private_operator_vehicle_evidence_path,
        max_length=260,
    )
    original_name = models.CharField(max_length=200, blank=True)
    content_type = models.CharField(max_length=60)
    file_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("period", "kind"), name="unique_operator_vehicle_evidence_kind"),
        ]


class OperatorRecordAccessAudit(models.Model):
    """No NI/document bytes are stored in activity log fields."""

    application = models.ForeignKey(
        UnifiedDriverApplication, on_delete=models.PROTECT, related_name="operator_record_audits",
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=30)
    reason = models.CharField(max_length=500)
    at = models.DateTimeField(auto_now_add=True)
