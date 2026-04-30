from django.db import models
from django.conf import settings

class Complaint(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints')
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Complaint by {self.user} - {self.title}"



class TripComplaint(models.Model):
    COMPLAINT_TYPE_CHOICES = [
        ('trip_issue', 'Trip Complaint'),
        ('driver_issue', 'Driver Issue'),
        ('service_issue', 'Service Issue'),
        ('payment_issue', 'Payment Issue'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trip_complaints')
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='complaints')
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_response = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Complaint #{self.pk} by {self.user.first_name}"


class LostProperty(models.Model):
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('under_investigation', 'Under Investigation'),
        ('found', 'Found'),
        ('returned', 'Returned'),
        ('not_found', 'Not Found'),
        ('closed', 'Closed'),
    ]
    
    ITEM_TYPE_CHOICES = [
        ('luggage', 'Luggage'),
        ('bag', 'Bag'),
        ('wallet', 'Wallet'),
        ('phone', 'Phone'),
        ('keys', 'Keys'),
        ('documents', 'Documents'),
        ('clothing', 'Clothing'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lost_property_reports')
    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='lost_property')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='other')
    item_description = models.TextField(help_text="Detailed description of the lost item")
    item_color = models.CharField(max_length=50, blank=True, null=True, help_text="Color of the item")
    item_brand = models.CharField(max_length=100, blank=True, null=True, help_text="Brand/make of the item")
    lost_location = models.CharField(max_length=255, blank=True, null=True, help_text="Where the item was lost (pickup/dropoff/vehicle)")
    contact_preference = models.CharField(max_length=20, choices=[
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('sms', 'SMS'),
    ], default='phone')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    photo = models.ImageField(upload_to='lost_property/photos/', blank=True, null=True, help_text="Photo of the lost item")
    admin_notes = models.TextField(blank=True, null=True)
    found_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lost Property #{self.pk} - {self.item_type} for {self.user.first_name}"

    class Meta:
        verbose_name_plural = "Lost Properties"

