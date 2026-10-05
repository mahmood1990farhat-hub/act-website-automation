from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trips", "0006_driver_details_reminder"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="guest_driver_licence_number",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="guest_driver_photo_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
