from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("admin_panel", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="instructionfile", name="language",
            field=models.CharField(blank=True, default="", max_length=5, choices=[
                ("en", "English"), ("ar", "العربية"), ("fr", "Français"),
                ("de", "Deutsch"), ("es", "Español"), ("tr", "Türkçe"), ("zh-CN", "简体中文"),
            ]),
        ),
        migrations.AlterField(
            model_name="instructionfile", name="file_type",
            field=models.CharField(max_length=50, help_text="Type of instruction file", choices=[
                ("TERMS_AND_CONDITIONS", "Terms and Conditions"), ("FAQ", "FAQ"),
                ("PRIVACY_POLICY", "Privacy Policy"), ("DRIVER_GUIDELINES", "Driver Guidelines"),
                ("PASSENGER_GUIDELINES", "Passenger Guidelines"), ("OTHER", "Other"),
            ]),
        ),
        migrations.AddConstraint(
            model_name="instructionfile",
            constraint=models.UniqueConstraint(fields=("file_type", "language"), name="instruction_type_language_unique"),
        ),
    ]
