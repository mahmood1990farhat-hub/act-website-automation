from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("drivers", "0002_professional_vehicle_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="basedriver",
            name="pco_licence_number",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="basedriver",
            name="driver_photo",
            field=models.ImageField(blank=True, null=True, upload_to="driver_docs/photos/"),
        ),
    ]
