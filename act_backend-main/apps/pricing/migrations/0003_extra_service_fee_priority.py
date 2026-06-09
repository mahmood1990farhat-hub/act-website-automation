from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0002_extra_service_fee'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='extraservicefee',
            options={
                'ordering': ['-priority', 'order', 'service_key', 'airport', 'vehicle_type', 'direction'],
                'verbose_name': 'Extra Service Fee',
                'verbose_name_plural': 'Extra Service Fees',
            },
        ),
        migrations.AlterField(
            model_name='extraservicefee',
            name='direction',
            field=models.CharField(
                choices=[('pickup', 'Pickup'), ('dropoff', 'Drop-off'), ('both', 'Both')],
                default='both',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='extraservicefee',
            name='priority',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Higher priority rules can override broader rules when pricing logic is added.',
            ),
        ),
    ]
