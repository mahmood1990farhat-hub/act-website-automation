from django.db import models


class PendingPayment(models.Model):
    payment_intent_id = models.CharField(max_length=255, unique=True, db_index=True, null=True, blank=True)
    price_breakdown = models.JSONField()  # Full pricing breakdown
    trip_data = models.JSONField()  # All trip details (pickup, dropoff, etc.)
    passenger_id = models.IntegerField(null=True, blank=True)  # FK to Passenger when available
    passenger_name = models.CharField(max_length=255, null=True, blank=True)
    passenger_email = models.EmailField(null=True, blank=True)
    passenger_country_code = models.CharField(max_length=64, null=True, blank=True)
    passenger_phone = models.CharField(max_length=32, null=True, blank=True)
    booking_details = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=3, default='GBP')  # ISO 4217 currency code
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_intent_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        pi_id = self.payment_intent_id or "Pending"
        return f"PendingPayment - {pi_id} - Expires: {self.expires_at}"



# Additive candidate records. No signal, view or payment call is registered here.
# The service module owns writes; do not expose these through generic admin CRUD.
import uuid


class BookingTermsAcceptance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pending_payment = models.OneToOneField(
        PendingPayment, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='accepted_terms_record',
    )
    trip = models.OneToOneField(
        'trips.Trip', null=True, blank=True, on_delete=models.PROTECT,
        related_name='accepted_terms_record',
    )
    payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    captured_pence = models.PositiveBigIntegerField(null=True, blank=True)
    snapshot = models.JSONField()
    snapshot_sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class CancellationReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.OneToOneField('trips.Trip', on_delete=models.PROTECT,
                               related_name='cancellation_receipt')
    received_at = models.DateTimeField()
    kind = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)


class RefundReservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.OneToOneField(CancellationReceipt, on_delete=models.PROTECT,
                                  related_name='refund_reservation')
    payment_intent_id = models.CharField(max_length=255)
    amount_pence = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default='GBP')
    assessment = models.JSONField()
    status = models.CharField(max_length=24, default='prepared')
    provider_refund_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    first_attempt_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(amount_pence__gt=0),
                                   name='act_reserved_refund_positive'),
            models.CheckConstraint(check=models.Q(status__in=[
                'prepared', 'in_flight', 'pending', 'requires_action',
                'succeeded', 'failed', 'canceled', 'reconcile',
            ]), name='act_reserved_refund_state'),
        ]

    @property
    def idempotency_key(self):
        return f'act-refund-{self.pk}'
