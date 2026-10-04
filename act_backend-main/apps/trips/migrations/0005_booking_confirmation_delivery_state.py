import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0004_booking_details_persistence"),
    ]

    operations = [
        migrations.AddField(
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
