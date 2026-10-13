# Public media file fields may be empty when genuine applicant documents
# are held in the private unified onboarding evidence store.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("drivers", "0004_unified_driver_application")]

    operations = [
        migrations.AlterField(
            model_name="basedriver",
            name="pco",
            field=models.FileField(blank=True, upload_to="driver_docs/pco/"),
        ),
        migrations.AlterField(
            model_name="basedriver",
            name="dbs",
            field=models.FileField(blank=True, upload_to="driver_docs/dbs/"),
        ),
        migrations.AlterField(
            model_name="basedriver",
            name="dvla",
            field=models.FileField(blank=True, upload_to="driver_docs/dvla/"),
        ),
    ]
