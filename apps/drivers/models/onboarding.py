from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class DriverOnboardingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('step1_approved', 'Step 1 Approved - Upload Documents'),
        ('step1_rejected', 'Step 1 Rejected'),
        ('documents_uploaded', 'Documents Uploaded - Pending Final Review'),
        ('final_approved', 'Final Approved'),
        ('final_rejected', 'Final Rejected'),
        ('needs_modification', 'Needs Modification'),
    ]
    
    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_onboarding_request')
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=15)
    email_address = models.EmailField()
    home_postcode = models.CharField(max_length=255)
    preferred_communication = models.CharField(max_length=20, choices=[
        ('phone', 'Phone Call'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    ])
    
    # Driving Experience
    years_experience = models.CharField(max_length=20, choices=[
        ('less_than_1', 'Less than 1 year'),
        ('1_to_3', '1–3 years'),
        ('3_to_5', '3–5 years'),
        ('5_plus', '5+ years'),
    ])
    previous_companies = models.JSONField(default=list, blank=True)  # Store list of companies
    familiar_areas = models.JSONField(default=list, blank=True)  # Store list of familiar areas
    preferred_journey_types = models.JSONField(default=list, blank=True)  # Store list of journey types
    
    # Vehicle Information
    vehicle_ownership = models.CharField(max_length=20, choices=[
        ('phv_owner', 'PHV Owner'),
        ('hiring_a_phv', 'Hiring a PHV'),
        ('do_not_have_a_phv', 'Do not have a PHV'),
        ('other', 'Other'),
    ])
    vehicle_type = models.CharField(max_length=50, choices=[
        ('5_seater_standard', '5-seater (Standard)'),
        ('7_seaters', '7 Seaters'),
        ('van_transporter', 'Van/Transporter'),
        ('other', 'Other'),
    ])
    fuel_type = models.CharField(max_length=20, choices=[
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('ev', 'Electric Vehicle (EV)'),
        ('plug_in_hybrid', 'Plug-in Hybrid'),
        ('hybrid', 'Hybrid'),
    ])
    
    # Preferences & Availability
    preferred_locations = models.JSONField(default=list, blank=True,)  # Store list of locations
    availability = models.CharField(max_length=20, choices=[
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('weekdays', 'Weekdays'),
        ('weekends', 'Weekends'),
        ('nights', 'Nights'),
        ('flexible', 'Flexible'),
    ])
    notification_method = models.CharField(max_length=20, choices=[
        ('app', 'Mobile App'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('no_preference', 'No Preference'),
    ])
    
    # Compliance & Safety
    has_tfl_licence = models.BooleanField(default=False)
    willing_dbs_check = models.BooleanField(default=False)
    agrees_policies = models.BooleanField(default=False)
    
    # Admin Review
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_onboarding_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Document Modification Tracking
    files_need_modification = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file names that need modification: ['pco', 'dbs', 'dvla', 'mot', 'phv']"
    )
    modification_confirmed = models.BooleanField(
        default=False,
        help_text="Whether driver has confirmed the file modifications"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Driver Onboarding Request'
        verbose_name_plural = 'Driver Onboarding Requests'
    
    def __str__(self):
        return f"Onboarding Request - {self.full_name} ({self.status})"
    
    def normalize_json_fields(self):
        """Ensure JSON fields are properly formatted as lists"""
        import json
        
        # Normalize previous_companies
        if isinstance(self.previous_companies, str):
            try:
                self.previous_companies = json.loads(self.previous_companies)
            except (json.JSONDecodeError, TypeError):
                self.previous_companies = []
        elif not isinstance(self.previous_companies, list):
            self.previous_companies = []
        
        # Normalize familiar_areas
        if isinstance(self.familiar_areas, str):
            try:
                self.familiar_areas = json.loads(self.familiar_areas)
            except (json.JSONDecodeError, TypeError):
                # If it's a comma-separated string, split it
                if ',' in self.familiar_areas:
                    self.familiar_areas = [area.strip() for area in self.familiar_areas.split(',') if area.strip()]
                else:
                    self.familiar_areas = []
        elif not isinstance(self.familiar_areas, list):
            self.familiar_areas = []
        
        # Normalize preferred_journey_types
        if isinstance(self.preferred_journey_types, str):
            try:
                self.preferred_journey_types = json.loads(self.preferred_journey_types)
            except (json.JSONDecodeError, TypeError):
                self.preferred_journey_types = []
        elif not isinstance(self.preferred_journey_types, list):
            self.preferred_journey_types = []
        
        # Normalize preferred_locations
        if isinstance(self.preferred_locations, str):
            try:
                self.preferred_locations = json.loads(self.preferred_locations)
            except (json.JSONDecodeError, TypeError):
                self.preferred_locations = []
        elif not isinstance(self.preferred_locations, list):
            self.preferred_locations = []
        
        # Normalize files_need_modification
        if isinstance(self.files_need_modification, str):
            try:
                self.files_need_modification = json.loads(self.files_need_modification)
            except (json.JSONDecodeError, TypeError):
                self.files_need_modification = []
        elif not isinstance(self.files_need_modification, list):
            self.files_need_modification = []
    
    def save(self, *args, **kwargs):
        """Override save to normalize JSON fields before saving"""
        self.normalize_json_fields()
        super().save(*args, **kwargs)
    
    def approve_step1(self, admin_user, notes=''):
        """Approve step 1 - questionnaire review"""
        # Update only the status and admin fields to avoid JSON field issues
        DriverOnboardingRequest.objects.filter(id=self.id).update(
            status='step1_approved',
            reviewed_by=admin_user,
            reviewed_at=timezone.now(),
            admin_notes=notes
        )
        
        # Refresh the instance to reflect changes
        self.refresh_from_db()
        
        # Activate user account so they can login and upload documents
        self.user.is_active = True
        self.user.save()
    
    def reject_step1(self, admin_user, reason):
        """Reject step 1 - questionnaire review"""
        # Update only the status and admin fields to avoid JSON field issues
        DriverOnboardingRequest.objects.filter(id=self.id).update(
            status='step1_rejected',
            reviewed_by=admin_user,
            reviewed_at=timezone.now(),
            rejection_reason=reason
        )
        self.refresh_from_db()
    
    def mark_documents_uploaded(self):
        """Mark that documents have been uploaded"""
        # Update only the status field to avoid JSON field issues
        DriverOnboardingRequest.objects.filter(id=self.id).update(
            status='documents_uploaded'
        )
        self.refresh_from_db()
    
    def approve_final(self, admin_user, notes=''):
        """Final approval - driver is fully approved"""
        # Update only the status and admin fields to avoid JSON field issues
        DriverOnboardingRequest.objects.filter(id=self.id).update(
            status='final_approved',
            reviewed_by=admin_user,
            reviewed_at=timezone.now(),
            admin_notes=notes
        )
        self.refresh_from_db()
        
        # Mark user as admin verified
        self.user.is_admin_verified = True
        self.user.save()
    
    def reject_final(self, admin_user, reason):
        """Final rejection"""
        # Update only the status and admin fields to avoid JSON field issues
        DriverOnboardingRequest.objects.filter(id=self.id).update(
            status='final_rejected',
            reviewed_by=admin_user,
            reviewed_at=timezone.now(),
            rejection_reason=reason
        )
        self.refresh_from_db()
    
    def request_modification(self, admin_user, reason, files_to_modify=None):
        """Request modification of specific documents"""
        files_to_modify = files_to_modify or []
        # Update fields - use instance save for JSONField to avoid serialization issues
        self.status = 'needs_modification'
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.files_need_modification = files_to_modify
        self.modification_confirmed = False
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'files_need_modification', 'modification_confirmed'])
