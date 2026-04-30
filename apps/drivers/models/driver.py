from django.db import models
from django.core.exceptions import ValidationError
from apps.office.models import Office
from apps.vehicle.models import Vehicle
from django.conf import settings
from .bank import BankDetails



class BaseDriver(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="base_driver")
    pco = models.FileField(upload_to="driver_docs/pco/")
    dbs = models.FileField(upload_to="driver_docs/dbs/")
    dvla = models.FileField(upload_to="driver_docs/dvla/")
    bank_details = models.ForeignKey(BankDetails, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_account_id = models.CharField(max_length=255, null=True, blank=True, help_text="Stripe Connect account ID")
    driver_commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Custom commission percentage for this driver. If null, uses vehicle type rule or default.",
        db_index=True
    )
    
    def clean(self):
        """Validate that driver_commission_percentage is between 0-100"""
        if self.driver_commission_percentage is not None:
            if self.driver_commission_percentage < 0 or self.driver_commission_percentage > 100:
                raise ValidationError({
                    'driver_commission_percentage': 'Driver commission percentage must be between 0 and 100'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)




class NormalDriver(models.Model):
    driver = models.OneToOneField(BaseDriver, on_delete=models.CASCADE, related_name="normal_driver")
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, related_name="normal_driver")



class OfficeDriver(models.Model):
    driver = models.OneToOneField(BaseDriver, on_delete=models.CASCADE, related_name="office_driver")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="office_drivers")
