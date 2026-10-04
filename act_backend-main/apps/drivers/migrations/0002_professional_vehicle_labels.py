from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="driveronboardingrequest",
            name="vehicle_type",
            field=models.CharField(
                choices=[
                    ("5_seater_standard", "Comfort Class"),
                    ("7_seaters", "Comfort XL"),
                    ("van_transporter", "Van/Transporter"),
                    ("other", "Other"),
                ],
                max_length=50,
            ),
        ),
    ]
