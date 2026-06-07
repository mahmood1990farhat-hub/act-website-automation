from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtraServiceFee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_key', models.CharField(choices=[('meet_greet', 'Meet & Greet Service'), ('child_seat', 'Child Seat'), ('infant_seat', 'Infant Seat'), ('booster_seat', 'Booster Seat'), ('wheelchair_assistance', 'Wheelchair Assistance')], max_length=50)),
                ('service_name_en', models.CharField(max_length=100)),
                ('service_name_ar', models.CharField(max_length=100)),
                ('direction', models.CharField(choices=[('pickup', 'Pickup'), ('dropoff', 'Dropoff'), ('both', 'Both')], default='both', max_length=10)),
                ('fee_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('pricing_mode', models.CharField(choices=[('fixed_fee', 'Fixed Fee'), ('per_item', 'Per Item')], default='fixed_fee', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('airport', models.ForeignKey(blank=True, help_text='Leave empty to apply to all airports.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='extra_service_fees', to='trips.airport')),
                ('vehicle_type', models.ForeignKey(blank=True, help_text='Leave empty to apply to all vehicle types.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='extra_service_fees', to='vehicle.vehicletype')),
            ],
            options={
                'verbose_name': 'Extra Service Fee',
                'verbose_name_plural': 'Extra Service Fees',
                'ordering': ['order', 'service_key', 'airport', 'vehicle_type', 'direction'],
            },
        ),
        migrations.AddIndex(
            model_name='extraservicefee',
            index=models.Index(fields=['service_key', 'is_active'], name='pricing_ext_service_75ce8e_idx'),
        ),
        migrations.AddIndex(
            model_name='extraservicefee',
            index=models.Index(fields=['airport', 'vehicle_type'], name='pricing_ext_airport_5094b5_idx'),
        ),
    ]
