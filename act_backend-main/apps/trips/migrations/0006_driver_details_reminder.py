from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0005_booking_confirmation_delivery_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="driver_details_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
