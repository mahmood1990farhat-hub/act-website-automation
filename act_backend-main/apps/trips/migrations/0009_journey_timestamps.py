from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0008_refund_outcome_tracking"),
    ]

    # Intentionally no data migration: historical actual times were not saved.
    operations = [
        migrations.AddField(
            model_name="trip",
            name="started_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="completed_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
    ]
