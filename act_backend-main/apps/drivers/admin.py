from django.contrib import admin
from .models import BankDetails , BaseDriver , NormalDriver, DriverOnboardingRequest
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

@admin.register(DriverOnboardingRequest)
class DriverOnboardingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'email_address', 'mobile_number', 'status', 
        'created_at', 'reviewed_at', 'actions_column'
    ]
    list_filter = ['status', 'created_at', 'reviewed_at', 'has_tfl_licence', 'willing_dbs_check']
    search_fields = ['full_name', 'email_address', 'mobile_number', 'home_postcode']
    readonly_fields = ['created_at', 'updated_at', 'reviewed_at', 'reviewed_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'mobile_number', 'email_address', 'home_postcode', 'preferred_communication')
        }),
        ('Driving Experience', {
            'fields': ('years_experience', 'previous_companies', 'familiar_areas', 'preferred_journey_types')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_ownership', 'vehicle_type', 'fuel_type')
        }),
        ('Preferences & Availability', {
            'fields': ('preferred_locations', 'availability', 'notification_method')
        }),
        ('Compliance & Safety', {
            'fields': ('has_tfl_licence', 'willing_dbs_check', 'agrees_policies')
        }),
        ('Admin Review', {
            'fields': ('status', 'admin_notes', 'rejection_reason', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def actions_column(self, obj):
        if obj.status == 'pending':
            approve_url = reverse('admin:drivers_driveronboardingrequest_approve', args=[obj.id])
            reject_url = reverse('admin:drivers_driveronboardingrequest_reject', args=[obj.id])
            return format_html(
                '<a class="button" href="{}">Approve Step 1</a> '
                '<a class="button" href="{}" style="background-color: #ba2121;">Reject Step 1</a>',
                approve_url, reject_url
            )
        elif obj.status == 'documents_uploaded':
            approve_url = reverse('admin:drivers_driveronboardingrequest_final_approve', args=[obj.id])
            reject_url = reverse('admin:drivers_driveronboardingrequest_final_reject', args=[obj.id])
            modify_url = reverse('admin:drivers_driveronboardingrequest_modify', args=[obj.id])
            return format_html(
                '<a class="button" href="{}">Final Approve</a> '
                '<a class="button" href="{}" style="background-color: #ba2121;">Final Reject</a> '
                '<a class="button" href="{}" style="background-color: #ffc107;">Request Modification</a>',
                approve_url, reject_url, modify_url
            )
        return format_html('<span style="color: #{};">{}</span>', 
                          '28a745' if obj.status in ['final_approved'] else 'dc3545' if obj.status in ['step1_rejected', 'final_rejected'] else 'ffc107', 
                          obj.status.replace('_', ' ').title())
    
    actions_column.short_description = 'Actions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'reviewed_by')

admin.site.register(BankDetails)
admin.site.register(BaseDriver)
admin.site.register(NormalDriver)



