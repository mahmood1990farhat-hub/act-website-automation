from django.db import models
from django.contrib.auth.models import AbstractUser



class CustomUser(AbstractUser):
    ACCOUNT_TYPES = [
        ("passenger", "Passenger"),
        ("normal_driver", "Normal Driver"),
        ("office_driver", "Office Driver"),
        ('office_owner' , 'office owner'),
    ]
    """
    I ensure unique for phone number and email in signup serializer so 
    if you try to create using query directly be carefull and check for Uniqueness 
    """
    username = models.CharField(max_length=150, unique=False , blank=True)
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    is_active = models.BooleanField(default=True)
    email = models.EmailField(unique = True)
    is_password_reset_ready = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15) 
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES, default="normal")
    address = models.CharField(max_length=255) 
    is_profile_completed = models.BooleanField(default=False)
    is_admin_verified = models.BooleanField(default=False)

    temp_email = models.EmailField(null=True, blank=True)
    temp_phone_number = models.CharField(max_length=15, null=True, blank=True)
    email_verification_in_progress = models.BooleanField(default=False)
    phone_verification_in_progress = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 

    def save(self, *args, **kwargs):
        # Ensure email is case insensitive
        if self.email:
            self.email = self.email.lower()

        super().save(*args, **kwargs)



    def __str__(self):
        return self.username



