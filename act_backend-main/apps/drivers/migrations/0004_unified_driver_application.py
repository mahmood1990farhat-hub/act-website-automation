# Additive unified application storage: legacy onboarding rows are untouched.
import django.db.models.deletion
from django.db import migrations, models
import apps.drivers.models.unified_application


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0003_passenger_driver_details"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnifiedDriverApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date_of_birth", models.DateField()),
                ("address", models.CharField(max_length=255)),
                ("postcode", models.CharField(max_length=20)),
                ("pco_badge_number", models.CharField(max_length=50)),
                ("pco_badge_expiry", models.DateField()),
                ("vehicle_class_code", models.CharField(blank=True, default="", max_length=32)),
                ("vehicle_make", models.CharField(blank=True, default="", max_length=80)),
                ("vehicle_model", models.CharField(blank=True, default="", max_length=80)),
                ("vehicle_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("vehicle_registration", models.CharField(blank=True, default="", max_length=50)),
                ("vehicle_colour", models.CharField(blank=True, default="", max_length=50)),
                ("mot_expiry", models.DateField(blank=True, null=True)),
                ("insurance_expiry", models.DateField(blank=True, null=True)),
                ("accepts_pets", models.BooleanField(blank=True, null=True)),
                ("ownership_explanation", models.CharField(blank=True, default="", max_length=500)),
                ("awaiting_vehicle", models.BooleanField(default=False)),
                ("passenger_photo_disclosure_consent", models.BooleanField(default=False)),
                ("setup_token_hash", models.CharField(blank=True, default="", max_length=64)),
                ("setup_token_expires_at", models.DateTimeField(blank=True, null=True)),
                ("setup_token_used_at", models.DateTimeField(blank=True, null=True)),
                ("welcome_email_sent_at", models.DateTimeField(blank=True, null=True)),
                ("password_set_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("onboarding_request", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="unified_application",
                    to="drivers.driveronboardingrequest",
                )),
            ],
        ),
        migrations.CreateModel(
            name="DriverApplicationDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[
                    ("pco_front", "TfL badge front"), ("pco_back", "TfL badge back"),
                    ("dvla_front", "DVLA licence front"), ("dvla_back", "DVLA licence back"),
                    ("driver_photo", "Driver profile photograph"), ("mot", "MOT certificate"),
                    ("insurance", "Vehicle insurance"), ("v5c", "V5C logbook"),
                    ("vehicle_phv", "Vehicle PHV licence"), ("hire_agreement", "Hired vehicle proof"),
                    ("dbs", "DBS certificate"),
                ], max_length=25)),
                ("file", models.FileField(
                    max_length=260,
                    storage=apps.drivers.models.unified_application.PrivateDriverDocumentStorage(),
                    upload_to=apps.drivers.models.unified_application.private_driver_upload_path,
                )),
                ("content_type", models.CharField(max_length=60)),
                ("original_name", models.CharField(blank=True, max_length=200)),
                ("file_size", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents",
                    to="drivers.unifieddriverapplication",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="driverapplicationdocument",
            constraint=models.UniqueConstraint(
                fields=("application", "kind"),
                name="unique_driver_application_document_kind",
            ),
        ),
    ]
