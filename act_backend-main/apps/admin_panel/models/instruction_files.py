from django.db import models
from django.conf import settings


class InstructionFile(models.Model):
    """
    Model for storing instruction files like Terms & Conditions, FAQ, Privacy Policy, etc.
    These files can be accessed publicly without authentication.
    """
    FILE_TYPE_CHOICES = [
        ('TERMS_AND_CONDITIONS', 'Terms and Conditions'),
        ('FAQ', 'FAQ'),
        ('PRIVACY_POLICY', 'Privacy Policy'),
        ('DRIVER_GUIDELINES', 'Driver Guidelines'),
        ('PASSENGER_GUIDELINES', 'Passenger Guidelines'),
        ('OTHER', 'Other'),
    ]
    
    file_type = models.CharField(
        max_length=50,
        choices=FILE_TYPE_CHOICES,
        unique=True,  # Only one active file per type
        help_text="Type of instruction file"
    )
    title = models.CharField(
        max_length=255,
        help_text="Title of the file (e.g., 'Terms and Conditions', 'FAQ')"
    )
    file = models.FileField(
        upload_to='instruction_files/',
        help_text="The instruction file (PDF, DOC, DOCX, etc.)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the file"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this file is currently active and should be shown to users"
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number of the file (incremented on updates)"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_instruction_files',
        help_text="Admin who uploaded this file"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_instruction_files',
        help_text="Admin who last updated this file"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'admin_panel'
        indexes = [
            models.Index(fields=['file_type', 'is_active']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_file_type_display()} - {self.title} (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Increment version if updating existing file
        if self.pk:
            try:
                old_instance = InstructionFile.objects.get(pk=self.pk)
                if old_instance.file != self.file:
                    self.version = old_instance.version + 1
            except InstructionFile.DoesNotExist:
                pass
        super().save(*args, **kwargs)
