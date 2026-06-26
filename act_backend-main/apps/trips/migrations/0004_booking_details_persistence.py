from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0003_trip_booking_confirmation_pdf_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="passenger_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="passenger_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="passenger_country_code",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="passenger_phone",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="trip",
            name="booking_details",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="trip",
            name="is_guest_checkout",
            field=models.BooleanField(default=False),
        ),
    ]
