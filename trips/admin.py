from django.contrib import admin
from django.utils.html import format_html
from .models import Airport


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Airport with geo-detection settings"""
    list_display = ['name_en', 'is_active', 'detection_area_display']
    list_filter = ['is_active']
    search_fields = ['name_en', 'name_ar']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name_en', 'name_ar', 'is_active')
        }),
        ('Geo-Detection', {
            'fields': ('detection_area',),
            'description': 'Polygon area for automatic airport detection. Pickup/dropoff within this area will be detected as airport trips. Use GeoJSON format or draw on map.'
        }),
        ('Default Fees', {
            'fields': ('pickup_vat', 'dropoff_vat'),
            'description': 'Default airport fees (used if no vehicle-specific fees are set)'
        }),
        ('Vehicle-Specific Fees (Optional)', {
            'fields': ('vehicle_specific_fees',),
            'description': 'Optional JSON: {vehicle_type_id: {"pickup_fee": X, "dropoff_fee": Y}}. Overrides default fees for specific vehicle types.',
            'classes': ('collapse',)
        }),
    )
    
    def detection_area_display(self, obj):
        """Display detection area status"""
        if obj.detection_area:
            return format_html('<span style="color: green;">✓ Area Set</span>')
        return format_html('<span style="color: red;">✗ No Area</span>')
    detection_area_display.short_description = 'Detection Area'