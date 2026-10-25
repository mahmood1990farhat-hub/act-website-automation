from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


TERMINAL_GUARD = """
CREATE FUNCTION act_guard_managed_cancelled_trip() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'cancelled' AND EXISTS (
      SELECT 1 FROM payments_cancellationcase c
      JOIN payments_cancellationreceipt r ON r.id = c.receipt_id
      WHERE r.trip_id = OLD.id
  ) AND (
      ROW(NEW.status, NEW.base_driver_id, NEW.is_guest_driver, NEW.guest_driver_name,
          NEW.guest_driver_phone, NEW.guest_driver_company, NEW.guest_driver_car_id,
          NEW.trip_date, NEW.trip_time, NEW.cost, NEW.is_paid, NEW.stripe_payment_intent,
          NEW.cancelled_at, NEW.cancelled_by_driver, NEW.cancelled_by_driver_id_id)
      IS DISTINCT FROM
      ROW(OLD.status, OLD.base_driver_id, OLD.is_guest_driver, OLD.guest_driver_name,
          OLD.guest_driver_phone, OLD.guest_driver_company, OLD.guest_driver_car_id,
          OLD.trip_date, OLD.trip_time, OLD.cost, OLD.is_paid, OLD.stripe_payment_intent,
          OLD.cancelled_at, OLD.cancelled_by_driver, OLD.cancelled_by_driver_id_id)
  ) THEN
    RAISE EXCEPTION 'Managed cancelled journey cannot be restarted, reassigned or repriced'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER act_managed_cancellation_terminal
BEFORE UPDATE ON trips_trip
FOR EACH ROW EXECUTE FUNCTION act_guard_managed_cancelled_trip();
"""


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0003_booking_terms_refund_records'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        # RefundPosting references an existing earnings model; its initial migration
        # is sufficient. No existing earnings schema or payout is changed.
        ('earnings', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='CancellationCase',
            fields=[
                ('receipt', models.OneToOneField(primary_key=True, serialize=False,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='managed_case', to='payments.cancellationreceipt')),
                ('original_status', models.CharField(max_length=20)),
                ('pickup_at', models.DateTimeField(blank=True, null=True)),
                ('stopped_at', models.DateTimeField()),
                ('hold_reason', models.CharField(blank=True, default='', max_length=80)),
                ('decision', models.JSONField(blank=True, default=dict)),
                ('requested_by', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'permissions': [('review_cancellationcase', 'Review ACT cancellation and refund cases')]},
        ),
        migrations.CreateModel(
            name='RefundPosting',
            fields=[
                ('reservation', models.OneToOneField(primary_key=True, serialize=False,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='accounting_posting', to='payments.refundreservation')),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('company_refund', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT, related_name='+', to='earnings.companyrefundledger')),
            ],
        ),
        migrations.RunSQL(TERMINAL_GUARD, reverse_sql='''
            DROP TRIGGER act_managed_cancellation_terminal ON trips_trip;
            DROP FUNCTION act_guard_managed_cancelled_trip();
        '''),
    ]
