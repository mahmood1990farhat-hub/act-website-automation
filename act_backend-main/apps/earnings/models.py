from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal
import uuid


class CommissionRule(models.Model):
    vehicle_type = models.ForeignKey('vehicle.VehicleType', null=True, blank=True, on_delete=models.CASCADE)
    company_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 20.00
    driver_percentage = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 80.00
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(company_percentage__gte=0) & Q(company_percentage__lte=100),
                name='valid_company_percentage'
            ),
            models.CheckConstraint(
                check=Q(driver_percentage__gte=0) & Q(driver_percentage__lte=100),
                name='valid_driver_percentage'
            ),
        ]
        unique_together = [['vehicle_type', 'is_active']]  # Only one active rule per vehicle type
    
    def clean(self):
        """Validate that percentages sum to 100"""
        if self.company_percentage + self.driver_percentage != 100:
            raise ValidationError({
                'driver_percentage': 'Company and driver percentages must sum to 100'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Calls clean() automatically
        super().save(*args, **kwargs)
    
    def __str__(self):
        vehicle_name = self.vehicle_type.name_en if self.vehicle_type else "Global"
        return f"{vehicle_name}: Company {self.company_percentage}% / Driver {self.driver_percentage}%"


class DriverEarningLedger(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),  # Trip completed, earnings calculated
        ('AVAILABLE', 'Available'),  # Ready for payout
        ('LOCKED', 'Locked'),  # Locked during bulk payout to prevent race conditions
        ('PROCESSING', 'Processing'),  # Payout initiated
        ('PAID', 'Paid'),  # Payout completed
    ]
    
    driver = models.ForeignKey('drivers.BaseDriver', on_delete=models.CASCADE, related_name='earnings')
    trip = models.OneToOneField('trips.Trip', on_delete=models.CASCADE, related_name='driver_earning')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # gross - commission
    currency = models.CharField(max_length=3, default='GBP')  # ISO 4217 currency code
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    stripe_transfer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_idempotency_key = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    payout_batch = models.ForeignKey('earnings.PayoutBatch', null=True, blank=True, on_delete=models.SET_NULL, related_name='earnings')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['trip']),
            models.Index(fields=['stripe_idempotency_key']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['trip'], name='unique_trip_earning')
        ]
    
    def __str__(self):
        return f"Earning #{self.id} - Driver {self.driver.id} - Trip {self.trip.id} - {self.net_amount} {self.currency}"


class CompanyRevenueLedger(models.Model):
    trip = models.OneToOneField('trips.Trip', on_delete=models.CASCADE, related_name='company_revenue')
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Commission amount
    currency = models.CharField(max_length=3, default='GBP')  # ISO 4217 currency code
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trip'], name='unique_trip_company_revenue')
        ]
    
    def __str__(self):
        return f"Company Revenue - Trip {self.trip.id} - {self.amount} {self.currency}"


class DriverRefundLedger(models.Model):
    REFUND_RULE_CHOICES = [
        ('FULL_REFUND', 'Full Refund'),  # Refund full net_amount
        ('PARTIAL_REFUND', 'Partial Refund'),  # Refund partial amount
        ('NO_REFUND', 'No Refund'),  # Earnings already paid, no refund to driver
    ]
    
    driver = models.ForeignKey('drivers.BaseDriver', on_delete=models.CASCADE, related_name='refunds')
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='driver_refunds')
    driver_earning = models.ForeignKey('earnings.DriverEarningLedger', on_delete=models.CASCADE, related_name='refunds', null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Negative amount (always negative)
    currency = models.CharField(max_length=3, default='GBP')  # ISO 4217 currency code
    refund_rule = models.CharField(max_length=20, choices=REFUND_RULE_CHOICES)
    stripe_refund_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_idempotency_key = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['driver', 'trip']),
            models.Index(fields=['stripe_idempotency_key']),
        ]
    
    def __str__(self):
        return f"Driver Refund - Trip {self.trip.id} - {self.refund_amount} {self.currency}"


class CompanyRefundLedger(models.Model):
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='company_refunds')
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Negative amount (always negative)
    currency = models.CharField(max_length=3, default='GBP')  # ISO 4217 currency code
    stripe_refund_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_idempotency_key = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['trip']),
            models.Index(fields=['stripe_idempotency_key']),
        ]
    
    def __str__(self):
        return f"Company Refund - Trip {self.trip.id} - {self.refund_amount} {self.currency}"


class PayoutBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),  # Batch created, not yet processed
        ('PROCESSING', 'Processing'),  # Stripe transfers initiated
        ('COMPLETED', 'Completed'),  # All transfers completed
        ('PARTIAL', 'Partial'),  # Some transfers failed
        ('FAILED', 'Failed'),  # All transfers failed
    ]
    
    batch_id = models.CharField(max_length=255, unique=True, db_index=True)  # UUID for batch
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    total_earnings = models.PositiveIntegerField(default=0)  # Count of earnings in batch
    successful_transfers = models.PositiveIntegerField(default=0)
    failed_transfers = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, related_name='payout_batches')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_log = models.JSONField(null=True, blank=True)  # Store errors for failed transfers
    
    class Meta:
        indexes = [
            models.Index(fields=['batch_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"PayoutBatch {self.batch_id} - {self.status} - {self.total_amount} {self.currency}"


class WithdrawalRequest(models.Model):
    """
    Tracks driver withdrawal requests for admin approval workflow.
    This model is for approval tracking only, NOT executing Stripe transfers.
    """
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),  # Driver submitted request, awaiting admin review
        ('APPROVED', 'Approved'),     # Admin approved, ready for payout
        ('REJECTED', 'Rejected'),     # Admin rejected the request
        ('CANCELED', 'Canceled'),     # Request canceled (by driver or admin)
        ('PAID', 'Paid'),             # Payout completed via PayoutBatch
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey('drivers.BaseDriver', on_delete=models.CASCADE, related_name='withdrawal_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                          help_text="Always NULL in MVP - pay all available earnings")
    currency = models.CharField(max_length=3, default='GBP')
    note = models.TextField(blank=True, help_text="Driver's message/note")
    reviewed_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='reviewed_withdrawals', help_text="Admin who reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, help_text="Admin's review note/reason")
    payout_batch = models.ForeignKey('earnings.PayoutBatch', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='withdrawal_requests', help_text="Payout batch that processed this request")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payout_batch']),
        ]
        constraints = [
            # One active request per driver until admin decision (REJECTED/CANCELED) or payout (PAID)
            models.UniqueConstraint(
                fields=['driver'],
                condition=Q(status__in=['SUBMITTED', 'APPROVED']),
                name='unique_driver_active_request'
            )
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"WithdrawalRequest {self.id} - Driver {self.driver.id} - {self.status}"

