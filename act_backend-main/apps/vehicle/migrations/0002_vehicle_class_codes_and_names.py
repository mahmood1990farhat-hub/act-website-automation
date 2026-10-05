from django.db import migrations, models


CLASS_MIGRATION = {
    "Standard PHV": ("comfort", "Comfort Class", "فئة الراحة"),
    "7 Seaters PHV": ("comfort_xl", "Comfort XL", "فئة الراحة XL"),
    "Luxury": ("executive", "Executive Class", "الفئة التنفيذية"),
    "Luxury Van": ("executive_xl", "Executive XL", "الفئة التنفيذية XL"),
    "VIP Business PHV": ("first_class", "First Class", "الدرجة الأولى"),
    # Idempotent support if a database was manually renamed before this migration.
    "Comfort Class": ("comfort", "Comfort Class", "فئة الراحة"),
    "Comfort XL": ("comfort_xl", "Comfort XL", "فئة الراحة XL"),
    "Executive Class": ("executive", "Executive Class", "الفئة التنفيذية"),
    "Executive XL": ("executive_xl", "Executive XL", "الفئة التنفيذية XL"),
    "First Class": ("first_class", "First Class", "الدرجة الأولى"),
}

REVERSE_NAMES = {
    "comfort": "Standard PHV",
    "comfort_xl": "7 Seaters PHV",
    "executive": "Luxury",
    "executive_xl": "Luxury Van",
    "first_class": "VIP Business PHV",
}


def migrate_vehicle_classes(apps, schema_editor):
    VehicleType = apps.get_model("vehicle", "VehicleType")
    for vehicle_type in VehicleType.objects.all().order_by("pk"):
        migrated = CLASS_MIGRATION.get(vehicle_type.name_en)
        if migrated:
            code, name_en, name_ar = migrated
            vehicle_type.code = code
            vehicle_type.name_en = name_en
            vehicle_type.name_ar = name_ar
            vehicle_type.save(update_fields=["code", "name_en", "name_ar"])
        else:
            # Preserve any custom/legacy class without guessing its business meaning.
            vehicle_type.code = f"legacy_{vehicle_type.pk}"
            vehicle_type.save(update_fields=["code"])


def reverse_vehicle_classes(apps, schema_editor):
    VehicleType = apps.get_model("vehicle", "VehicleType")
    for vehicle_type in VehicleType.objects.all():
        old_name = REVERSE_NAMES.get(vehicle_type.code)
        if old_name:
            vehicle_type.name_en = old_name
            vehicle_type.save(update_fields=["name_en"])


class Migration(migrations.Migration):
    dependencies = [
        ("vehicle", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicletype",
            name="code",
            field=models.CharField(max_length=32, null=True, unique=True),
        ),
        migrations.RunPython(migrate_vehicle_classes, reverse_vehicle_classes),
        migrations.AlterField(
            model_name="vehicletype",
            name="code",
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
