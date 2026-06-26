from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pendingpayment",
            name="passenger_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pendingpayment",
            name="passenger_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="pendingpayment",
            name="passenger_email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="pendingpayment",
            name="passenger_country_code",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="pendingpayment",
            name="passenger_phone",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="pendingpayment",
            name="booking_details",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
