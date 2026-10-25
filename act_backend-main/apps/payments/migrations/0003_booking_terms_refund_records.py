import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0002_booking_details_persistence'),
        ('trips', '0008_refund_outcome_tracking'),
    ]
    operations = [
        migrations.CreateModel(
            name='BookingTermsAcceptance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_intent_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('captured_pence', models.PositiveBigIntegerField(blank=True, null=True)),
                ('snapshot', models.JSONField()),
                ('snapshot_sha256', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pending_payment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_terms_record', to='payments.pendingpayment')),
                ('trip', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='accepted_terms_record', to='trips.trip')),
            ],
        ),
        migrations.CreateModel(
            name='CancellationReceipt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('received_at', models.DateTimeField()),
                ('kind', models.CharField(max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('trip', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='cancellation_receipt', to='trips.trip')),
            ],
        ),
        migrations.CreateModel(
            name='RefundReservation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_intent_id', models.CharField(max_length=255)),
                ('amount_pence', models.PositiveBigIntegerField()),
                ('currency', models.CharField(default='GBP', max_length=3)),
                ('assessment', models.JSONField()),
                ('status', models.CharField(default='prepared', max_length=24)),
                ('provider_refund_id', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('first_attempt_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('receipt', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='refund_reservation', to='payments.cancellationreceipt')),
            ],
            options={'constraints': [
                models.CheckConstraint(check=models.Q(amount_pence__gt=0), name='act_reserved_refund_positive'),
                models.CheckConstraint(check=models.Q(status__in=[
                    'prepared', 'in_flight', 'pending', 'requires_action', 'succeeded',
                    'failed', 'canceled', 'reconcile']), name='act_reserved_refund_state'),
            ]},
        ),
    ]
