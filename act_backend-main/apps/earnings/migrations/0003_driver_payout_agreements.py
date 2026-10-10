import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('earnings', '0002_driver_commission_groups')]

    # Additive schema only. Do not manufacture accepted rates for historical trips.
    operations = [
        migrations.CreateModel(
            name='DriverPayoutAgreement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('gross_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('company_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('commission_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('net_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='GBP', max_length=3)),
                ('accepted_at', models.DateTimeField(auto_now_add=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payout_agreements', to='drivers.basedriver')),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payout_agreements', to='trips.trip')),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=['trip'], condition=models.Q(released_at__isnull=True), name='one_current_driver_payout'),
                    models.CheckConstraint(check=models.Q(company_percentage__gte=0, company_percentage__lte=100), name='payout_percentage_in_range'),
                    models.CheckConstraint(check=models.Q(gross_amount__gte=0, commission_amount__gte=0, net_amount__gte=0), name='payout_amounts_nonnegative'),
                    models.CheckConstraint(check=models.Q(gross_amount=models.F('commission_amount') + models.F('net_amount')), name='payout_amounts_balance'),
                ],
            },
        ),
    ]
