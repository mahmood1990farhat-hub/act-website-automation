from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0007_external_driver_passenger_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="refund_status",
            field=models.CharField(default="not_applicable", max_length=32),
        ),
        migrations.AddField(
            model_name="trip",
            name="stripe_refund_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="refund_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="refund_error",
            field=models.TextField(blank=True, default=""),
        ),
    ]
