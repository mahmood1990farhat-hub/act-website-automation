import uuid

from django.db import migrations, models


def populate_booking_confirmation_tokens(apps, schema_editor):
    Trip = apps.get_model("trips", "Trip")
    for trip in Trip.objects.filter(booking_confirmation_token__isnull=True).iterator():
        trip.booking_confirmation_token = uuid.uuid4()
        trip.save(update_fields=["booking_confirmation_token"])


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0004_booking_details_persistence"),
    ]

    operations = [
        # Existing production rows must receive distinct values before the
        # database enforces uniqueness/non-null.
        migrations.AddField(
            model_name="trip",
            name="booking_confirmation_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(
            populate_booking_confirmation_tokens,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="trip",
            name="booking_confirmation_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="passenger_confirmation_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="internal_booking_notification_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
