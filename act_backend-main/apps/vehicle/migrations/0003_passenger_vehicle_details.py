from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vehicle", "0002_vehicle_class_codes_and_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="make",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="model",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="color",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
