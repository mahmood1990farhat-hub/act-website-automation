# TfL operator register: additive only; no existing/legacy data modifications.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("drivers", "0005_unified_private_driver_documents")]

    operations = [
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="national_insurance_ciphertext",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="registered_keeper_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="registered_keeper_address",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="driver_available_from",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="driver_ceased_available_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="vehicle_available_from",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="vehicle_ceased_available_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="unifieddriverapplication",
            name="operator_record_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
