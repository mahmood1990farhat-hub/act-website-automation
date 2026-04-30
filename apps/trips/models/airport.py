from django.contrib.gis.db import models 

class Airport(models.Model):
    name_en = models.CharField(max_length=255, verbose_name="Airport Name (English)")
    name_ar = models.CharField(max_length=255, verbose_name="Airport Name (Arabic)")

    pickup_vat = models.FloatField()
    dropoff_vat = models.FloatField()
    
    detection_area = models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Polygon area for automatic airport detection. Pickup/dropoff within this area will be detected as airport trips."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this airport is active for automatic detection"
    )
    
    # Optional per-vehicle pricing (stored as JSON for flexibility)
    vehicle_specific_fees = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional: {vehicle_type_id: {'pickup_fee': X, 'dropoff_fee': Y}}"
    )

    def __str__(self):
        return self.name_en
