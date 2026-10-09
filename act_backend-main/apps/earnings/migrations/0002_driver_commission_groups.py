from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("earnings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverCommissionGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("company_percentage", models.DecimalField(decimal_places=2, max_digits=5)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="DriverCommissionMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("driver", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="commission_membership", to="drivers.basedriver")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="earnings.drivercommissiongroup")),
            ],
        ),
    ]
