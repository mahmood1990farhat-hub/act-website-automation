from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import Q
from .models import PricingSettings, PricingTier, PeakTimeRule, AirportFee


@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for PricingSettings (singleton).
    Only one instance can exist (pk=1).
    """
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        return not PricingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of singleton
        return False
    
    def get_queryset(self, request):
        # Always return the singleton instance
        qs = super().get_queryset(request)
        if not qs.exists():
            # Create default instance if none exists
            PricingSettings.get_settings()
        return qs.filter(pk=1)
    
    list_display = ['__str__', 'vat_rate', 'minimum_fare', 'maximum_distance_miles', 'use_dynamic_pricing']
    fieldsets = (
        ('Global Settings', {
            'fields': ('vat_rate', 'minimum_fare', 'maximum_distance_miles', 'currency')
        }),
        ('Peak Pricing', {
            'fields': ('default_peak_multiplier',)
        }),
        ('Feature Flags', {
            'fields': ('use_dynamic_pricing',),
            'description': 'Enable dynamic pricing engine. When disabled, system uses legacy hardcoded pricing.'
        }),
    )


class PricingTierInline(admin.TabularInline):
    """Inline admin for pricing tiers within VehicleType admin"""
    model = PricingTier
    extra = 0
    fields = ('min_distance_miles', 'max_distance_miles', 'rate_per_mile', 'order', 'is_active')
    ordering = ('min_distance_miles',)


@admin.register(PricingTier)
class PricingTierAdmin(admin.ModelAdmin):
    """Admin interface for PricingTier"""
    list_display = ['vehicle_type', 'distance_range', 'rate_per_mile', 'is_active', 'order']
    list_filter = ['vehicle_type', 'is_active']
    search_fields = ['vehicle_type__name_en', 'vehicle_type__name_ar']
    ordering = ['vehicle_type', 'min_distance_miles']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vehicle_type', 'is_active', 'order')
        }),
        ('Distance Range', {
            'fields': ('min_distance_miles', 'max_distance_miles'),
            'description': 'Distance range in miles. Max distance is exclusive (e.g., 0-10 means 0 <= distance < 10)'
        }),
        ('Pricing', {
            'fields': ('rate_per_mile',)
        }),
    )
    
    def distance_range(self, obj):
        """Display distance range in a readable format"""
        return f"{obj.min_distance_miles} - {obj.max_distance_miles} mi"
    distance_range.short_description = 'Distance Range'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle_type')


@admin.register(PeakTimeRule)
class PeakTimeRuleAdmin(admin.ModelAdmin):
    """Admin interface for PeakTimeRule"""
    list_display = ['name', 'vehicle_type_display', 'time_range', 'days_display', 'multiplier', 'priority', 'is_active']
    list_filter = ['is_active', 'vehicle_type', 'priority']
    search_fields = ['name']
    ordering = ['-priority', 'start_time']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active', 'priority')
        }),
        ('Time Range', {
            'fields': ('start_time', 'end_time'),
            'description': 'Time range for peak pricing. Supports ranges that span midnight (e.g., 22:00-02:00)'
        }),
        ('Days of Week', {
            'fields': ('days_of_week',),
            'description': 'Select days when this rule applies. 0=Monday, 6=Sunday'
        }),
        ('Pricing', {
            'fields': ('multiplier', 'vehicle_type'),
            'description': 'Multiplier to apply to base rate. Leave vehicle type empty for global rule.'
        }),
    )
    
    def vehicle_type_display(self, obj):
        """Display vehicle type or 'All Vehicles'"""
        return obj.vehicle_type.name_en if obj.vehicle_type else 'All Vehicles'
    vehicle_type_display.short_description = 'Vehicle Type'
    
    def time_range(self, obj):
        """Display time range"""
        return f"{obj.start_time} - {obj.end_time}"
    time_range.short_description = 'Time Range'
    
    def days_display(self, obj):
        """Display days of week in readable format"""
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        days = [day_names[day] for day in sorted(obj.days_of_week)]
        return ', '.join(days) if days else 'None'
    days_display.short_description = 'Days'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vehicle_type')


@admin.register(AirportFee)
class AirportFeeAdmin(admin.ModelAdmin):
    """Admin interface for AirportFee (per-vehicle airport fees)"""
    list_display = ['airport', 'vehicle_type', 'pickup_fee', 'dropoff_fee']
    list_filter = ['airport', 'vehicle_type']
    search_fields = ['airport__name_en', 'airport__name_ar', 'vehicle_type__name_en']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('airport', 'vehicle_type')
        }),
        ('Fees', {
            'fields': ('pickup_fee', 'dropoff_fee'),
            'description': 'Vehicle-specific fees. If not set, uses airport default fees.'
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('airport', 'vehicle_type')

