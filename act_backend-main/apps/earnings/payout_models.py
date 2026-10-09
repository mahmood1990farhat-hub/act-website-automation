"""Private, append-only financial terms captured when an ACT driver accepts.

These records are not payable earnings until the existing completion service
creates the ledgers. They must never be exposed through a passenger/driver
ModelSerializer with fields='__all__'.
"""
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class PayoutAgreementQuerySet(models.QuerySet):
    def update(self, **kwargs):
        # Financial corrections belong in adjustment records, not in this history.
        if set(kwargs) != {'released_at'} or kwargs['released_at'] is None:
            raise ValidationError('Accepted payout terms cannot be rewritten.')
        return super().filter(released_at__isnull=True).update(**kwargs)

    def delete(self):
        raise ValidationError('Accepted payout history cannot be deleted.')


class DriverPayoutAgreement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey('trips.Trip', on_delete=models.PROTECT, related_name='payout_agreements')
    driver = models.ForeignKey('drivers.BaseDriver', on_delete=models.PROTECT, related_name='payout_agreements')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    company_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    accepted_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    objects = PayoutAgreementQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trip'], condition=Q(released_at__isnull=True), name='one_current_driver_payout'),
            models.CheckConstraint(check=Q(company_percentage__gte=0, company_percentage__lte=100), name='payout_percentage_in_range'),
            models.CheckConstraint(check=Q(gross_amount__gte=0, commission_amount__gte=0, net_amount__gte=0), name='payout_amounts_nonnegative'),
            models.CheckConstraint(check=Q(gross_amount=F('commission_amount') + F('net_amount')), name='payout_amounts_balance'),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Accepted payout terms cannot be rewritten.')
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Accepted payout history cannot be deleted.')
