from django.db import models
from apps.office.models import Office


class VehicleType(models.Model):
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)
    desc_en = models.TextField(blank=True)
    desc_ar = models.TextField(blank=True)
    icon = models.ImageField(upload_to='vehicle_types/icons/')
    max_passengers_count = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        ordering = ['order'] 


class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=50)
    mot = models.FileField(upload_to="vehicles/mot/")
    year_of_manufacture = models.PositiveIntegerField()
    phv = models.FileField(upload_to="vehicles/phv/")
    vehicle_type = models.ForeignKey('VehicleType', on_delete=models.SET_NULL, null=True, blank=True, related_name="vehicles")

    def __str__(self):
        return self.vehicle_number


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='vehicles/images/')


class OfficeVehicle(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="office_vehicles")
    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="office_vehicles")


