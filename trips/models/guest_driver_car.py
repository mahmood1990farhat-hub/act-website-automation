from django.db import models


class GuestDriverCar(models.Model):
    """
    Car information for guest/external drivers assigned to trips.
    Each trip assignment can have its own car information.
    """
    brand = models.CharField(max_length=100, help_text="Car brand (e.g., Toyota, Mercedes)")
    model = models.CharField(max_length=100, help_text="Car model (e.g., Camry, E-Class)")
    color = models.CharField(max_length=50, help_text="Car color (e.g., Black, White, Silver)")
    registration_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Vehicle registration/license plate number"
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Year of manufacture (optional)"
    )
    additional_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about the car (e.g., 'Clean interior', 'GPS installed')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['registration_number']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.brand} {self.model} - {self.registration_number}"
