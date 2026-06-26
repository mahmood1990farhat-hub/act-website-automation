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



