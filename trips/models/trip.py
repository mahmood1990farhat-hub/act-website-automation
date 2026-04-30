from django.db import models 
from django.utils import timezone
from apps.vehicle.models import VehicleType
from apps.office.models import Office
from apps.drivers.models import BaseDriver
from apps.passengers.models import  Passenger
from .airport import Airport



class Trip(models.Model):
    AIRPORT_DIRECTION_CHOICES = [
        ('from', 'From Airport'),
        ('to', 'To Airport'),
    ]
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("driver_on_the_way", "Driver on the way"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )

    pickup_place_id = models.CharField(max_length=255, blank=True, null=True)
    pickup_str = models.CharField(max_length=500, blank=True, null=True)
    pickup_postal_code = models.CharField(max_length=20, blank=True, null=True)
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()


    dropoff_place_id = models.CharField(max_length=255, blank=True, null=True)
    dropoff_str = models.CharField(max_length=500, blank=True, null=True)
    dropoff_postal_code = models.CharField(max_length=20, blank=True, null=True)
    dropoff_lat = models.FloatField()
    dropoff_lng = models.FloatField()
    
    route_polyline = models.TextField(blank=True, null=True)


    expected_trip_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated trip duration in minutes"
    )

    distance_miles = models.FloatField(
        null=True,
        blank=True,
        help_text="Estimated distance in miles"
    )

    trip_date = models.DateField()
    trip_time = models.TimeField()
    car_type = models.ForeignKey(VehicleType, on_delete=models.SET_NULL, null=True, related_name="trips")
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    passengers_count = models.PositiveIntegerField()


    passenger = models.ForeignKey(Passenger, on_delete=models.SET_NULL, null=True, related_name="trips")
    base_driver = models.ForeignKey(BaseDriver, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips")


    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    airport = models.ForeignKey(
        Airport, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='trips',
        help_text="If trip starts or ends at an airport"
    )

    airport_direction = models.CharField(
        max_length=5,
        choices=AIRPORT_DIRECTION_CHOICES,
        null=True,
        help_text="Indicates if the airport is for pickup or dropoff"
    )
    large_suitcase = models.PositiveIntegerField(default=0)
    small_suitcase = models.PositiveIntegerField(default=0)
    
    stripe_payment_intent = models.CharField(max_length=255, unique=True, null=True, blank=True)
    last4 = models.CharField(max_length=4, null=True, blank=True)
    card_brand = models.CharField(max_length=20, null=True, blank=True)
    is_paid = models.BooleanField(default= False)
    booking_confirmation_pdf = models.FileField(
        upload_to="trips/booking_confirmations/",
        null=True,
        blank=True
    )
    cancellation_confirmation_pdf = models.FileField(
        upload_to="trips/cancellation_confirmations/",
        null=True,
        blank=True
    )
    
    # Pricing breakdown fields
    base_trip_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    regular_vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    airport_vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_adjustment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Guest/External Driver fields
    is_guest_driver = models.BooleanField(default=False, help_text="True if assigned to external/guest driver")
    guest_driver_name = models.CharField(max_length=255, blank=True, null=True, help_text="Name of guest driver")
    guest_driver_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Phone number of guest driver")
    guest_driver_company = models.CharField(max_length=255, blank=True, null=True, help_text="Company name (e.g., Uber, Bolt)")
    guest_driver_car = models.ForeignKey(
        'trips.GuestDriverCar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trips',
        help_text="Car information for guest driver assigned to this trip"
    )
    
    # Driver Cancellation fields
    cancelled_by_driver = models.BooleanField(default=False, help_text="True if driver cancelled this trip")
    cancelled_by_driver_id = models.ForeignKey(
        BaseDriver, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='cancelled_trips',
        help_text="Driver who cancelled this trip"
    )
    cancellation_reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation")
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="When the trip was cancelled")

    def cancel_by_driver(self, driver, cancellation_reason=None):
        """
        Reusable method to cancel a trip by a driver (or admin on behalf of driver).
        
        This method:
        - Sets trip status to 'pending' (making it available for other drivers)
        - Unassigns the current driver (base_driver = None)
        - Marks the trip as cancelled by the specified driver
        - Clears guest driver fields
        - Records cancellation timestamp and reason
        
        Args:
            driver: BaseDriver instance - the driver who is cancelling (or was assigned before admin cancellation)
            cancellation_reason: Optional string - reason for cancellation
            
        Returns:
            None (modifies self in place)
            
        Note:
            This method does NOT save the trip. Call save() after calling this method.
            This allows the caller to use it within a transaction with select_for_update().
        """
        # Store the driver who was assigned (for tracking purposes)
        original_driver = self.base_driver or driver
        
        # Mark as cancelled by driver
        self.cancelled_by_driver = True
        self.cancelled_by_driver_id = original_driver  # Track which driver was cancelled
        self.cancelled_at = timezone.now()
        
        if cancellation_reason:
            self.cancellation_reason = cancellation_reason
        
        # Unassign driver - make trip available for reassignment
        self.base_driver = None
        self.status = 'pending'  # Make available for other drivers
        
        # Clear guest driver fields if set
        self.is_guest_driver = False
        self.guest_driver_name = None
        self.guest_driver_phone = None
        self.guest_driver_company = None

    def __str__(self):
        return f"Trip #{self.pk} - {self.passenger.user.username if self.passenger else 'No Passenger'}"



class StopPoint(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stop_points")
    point_lat = models.FloatField()
    point_lng = models.FloatField()
    point_place_id = models.CharField(max_length=255, blank=True, null=True)
    point_postal_code = models.CharField(max_length=20, blank=True, null=True)
    point_str = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StopPoint for Trip #{self.trip_id} at {self.point_lat},{self.point_lng}"








