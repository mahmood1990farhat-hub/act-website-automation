# Record original and replacement vehicle periods without changing legacy drivers.
import apps.drivers.models.unified_application
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0006_unified_operator_records"),
        ("vehicle", "0003_passenger_vehicle_details"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OperatorVehiclePeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_registration", models.CharField(max_length=50)),
                ("vehicle_make", models.CharField(max_length=80)),
                ("vehicle_model", models.CharField(max_length=80)),
                ("vehicle_colour", models.CharField(max_length=50)),
                ("vehicle_class_code", models.CharField(max_length=32)),
                ("vehicle_year", models.PositiveSmallIntegerField()),
                ("ownership", models.CharField(max_length=20)),
                ("registered_keeper_name", models.CharField(max_length=150)),
                ("registered_keeper_address", models.CharField(max_length=500)),
                ("available_from", models.DateTimeField()),
                ("ceased_at", models.DateTimeField(blank=True, null=True)),
                ("close_reason", models.CharField(blank=True, default="", max_length=500)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="operator_vehicle_periods",
                    to="drivers.unifieddriverapplication",
                )),
                ("vehicle", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+",
                    to="vehicle.vehicle",
                )),
                ("reviewed_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("closed_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="+", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-available_from", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="operatorvehicleperiod",
            constraint=models.UniqueConstraint(
                fields=("application",), condition=models.Q(ceased_at__isnull=True),
                name="unique_active_unified_vehicle_period",
            ),
        ),
        migrations.CreateModel(
            name="OperatorVehicleEvidence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[
                    ("mot", "MOT certificate"), ("insurance", "Insurance certificate"),
                    ("vehicle_phv", "PHV vehicle licence"), ("v5c", "V5C logbook"),
                    ("hire_agreement", "Proof of lawful hire"),
                ], max_length=25)),
                ("file", models.FileField(
                    storage=apps.drivers.models.unified_application.PrivateDriverDocumentStorage(),
                    upload_to=apps.drivers.models.unified_application.private_operator_vehicle_evidence_path,
                    max_length=260,
                )),
                ("original_name", models.CharField(blank=True, max_length=200)),
                ("content_type", models.CharField(max_length=60)),
                ("file_size", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("period", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="evidence",
                    to="drivers.operatorvehicleperiod",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="operatorvehicleevidence",
            constraint=models.UniqueConstraint(
                fields=("period", "kind"), name="unique_operator_vehicle_evidence_kind",
            ),
        ),
        migrations.CreateModel(
            name="OperatorRecordAccessAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=30)),
                ("reason", models.CharField(max_length=500)),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("application", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="operator_record_audits",
                    to="drivers.unifieddriverapplication",
                )),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="+",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
