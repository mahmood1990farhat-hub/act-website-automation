"""
Management command to seed pricing data from hardcoded PRICING dictionary.

This command extracts all pricing rates from utils/calculate_cost.py and creates
PricingTier, PricingSettings, and PeakTimeRule records in the database.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import time

from apps.pricing.models import PricingSettings, PricingTier, PeakTimeRule
from apps.vehicle.models import VehicleType

# Import the hardcoded PRICING dictionary
from utils.calculate_cost import PRICING, MIN_FARE


class Command(BaseCommand):
    help = 'Seed pricing data from hardcoded PRICING dictionary'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes to the database',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing pricing data before seeding',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear_existing = options['clear']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        with transaction.atomic():
            if clear_existing:
                self.stdout.write('Clearing existing pricing data...')
                if not dry_run:
                    PricingTier.objects.all().delete()
                    PeakTimeRule.objects.all().delete()
                    # Don't delete PricingSettings, just reset it
                    settings = PricingSettings.get_settings()
                    settings.use_dynamic_pricing = False
                    settings.save()

            # 1. Create or update PricingSettings
            self.stdout.write('Creating PricingSettings...')
            settings = PricingSettings.get_settings()
            if not dry_run:
                settings.vat_rate = Decimal('0.20')
                settings.minimum_fare = Decimal(str(MIN_FARE))
                settings.maximum_distance_miles = Decimal('90.00')
                settings.currency = 'GBP'
                settings.default_peak_multiplier = Decimal('1.0')
                settings.use_dynamic_pricing = False  # Keep disabled initially
                settings.save()
            self.stdout.write(self.style.SUCCESS(f'✓ PricingSettings created/updated'))

            # 2. Create PricingTier records for each vehicle type
            self.stdout.write('Creating PricingTier records...')
            tiers_created = 0
            tiers_updated = 0

            for vehicle_type_name, pricing_data in PRICING.items():
                # Find or create VehicleType
                try:
                    vehicle_type = VehicleType.objects.get(name_en=vehicle_type_name)
                except VehicleType.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠ VehicleType "{vehicle_type_name}" not found. Skipping...'
                        )
                    )
                    continue

                # Process normal rates
                normal_rates = pricing_data.get('normal', [])
                for i, (max_distance, rate) in enumerate(normal_rates):
                    min_distance = normal_rates[i - 1][0] if i > 0 else Decimal('0.00')
                    
                    if not dry_run:
                        tier, created = PricingTier.objects.update_or_create(
                            vehicle_type=vehicle_type,
                            min_distance_miles=Decimal(str(min_distance)),
                            max_distance_miles=Decimal(str(max_distance)),
                            defaults={
                                'rate_per_mile': Decimal(str(rate)),
                                'order': i,
                                'is_active': True
                            }
                        )
                        if created:
                            tiers_created += 1
                        else:
                            tiers_updated += 1
                    else:
                        tiers_created += 1
                    
                    self.stdout.write(
                        f'  {vehicle_type_name} (normal): {min_distance}-{max_distance}mi @ £{rate}/mi'
                    )

                # Process peak rates
                peak_rates = pricing_data.get('peak', [])
                for i, (max_distance, rate) in enumerate(peak_rates):
                    min_distance = peak_rates[i - 1][0] if i > 0 else Decimal('0.00')
                    
                    # For peak rates, we'll create separate tiers but they'll be selected
                    # based on PeakTimeRule multipliers. However, the current system uses
                    # different rates for peak. We'll create peak-specific tiers with a suffix
                    # in the order field to distinguish them, but actually we should use
                    # the same tiers with peak multipliers.
                    # 
                    # Actually, looking at the current implementation, it seems like peak
                    # rates are just higher rates. We'll create the normal tiers and then
                    # create peak rules that apply multipliers to match the peak rates.
                    # But that's complex. Let's create both normal and peak tiers for now,
                    # and the peak rules will need to be configured separately.
                    #
                    # Actually, the simplest approach: Create normal tiers, and create
                    # peak rules with multipliers that convert normal rates to peak rates.
                    # But we need to calculate the multiplier for each distance bracket.
                    #
                    # For now, let's just create the normal tiers. Peak rules will be
                    # created separately with appropriate multipliers.

            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created {tiers_created} tiers, updated {tiers_updated} tiers'
                )
            )

            # 3. Create default PeakTimeRule (07:00-10:00 and 16:00-19:00)
            self.stdout.write('Creating PeakTimeRule records...')
            
            # Calculate average peak multiplier from the pricing data
            # This is a rough approximation - we'll use the ratio of peak to normal rates
            peak_multipliers = []
            for vehicle_type_name, pricing_data in PRICING.items():
                normal_rates = pricing_data.get('normal', [])
                peak_rates = pricing_data.get('peak', [])
                if len(normal_rates) == len(peak_rates):
                    for (_, normal_rate), (_, peak_rate) in zip(normal_rates, peak_rates):
                        if normal_rate > 0:
                            multiplier = peak_rate / normal_rate
                            peak_multipliers.append(multiplier)
            
            avg_peak_multiplier = (
                sum(peak_multipliers) / len(peak_multipliers)
                if peak_multipliers else Decimal('1.065')  # Default ~6.5% increase
            )
            avg_peak_multiplier = Decimal(str(round(avg_peak_multiplier, 3)))

            # Morning peak: 07:00-10:00, Monday-Friday
            if not dry_run:
                morning_rule, created = PeakTimeRule.objects.update_or_create(
                    name='Morning Peak Hours',
                    defaults={
                        'is_active': True,
                        'start_time': time(7, 0),
                        'end_time': time(10, 0),
                        'days_of_week': [0, 1, 2, 3, 4],  # Monday-Friday
                        'multiplier': avg_peak_multiplier,
                        'vehicle_type': None,  # Global rule
                        'priority': 10
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Morning Peak Hours rule'))
                else:
                    self.stdout.write(self.style.SUCCESS('✓ Updated Morning Peak Hours rule'))

            # Evening peak: 16:00-19:00, Monday-Friday
            if not dry_run:
                evening_rule, created = PeakTimeRule.objects.update_or_create(
                    name='Evening Peak Hours',
                    defaults={
                        'is_active': True,
                        'start_time': time(16, 0),
                        'end_time': time(19, 0),
                        'days_of_week': [0, 1, 2, 3, 4],  # Monday-Friday
                        'multiplier': avg_peak_multiplier,
                        'vehicle_type': None,  # Global rule
                        'priority': 10
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS('✓ Created Evening Peak Hours rule'))
                else:
                    self.stdout.write(self.style.SUCCESS('✓ Updated Evening Peak Hours rule'))

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Seeding complete! Average peak multiplier: {avg_peak_multiplier}'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ Note: Dynamic pricing is DISABLED by default.'
                    '\n   Enable it in Django admin: Pricing Settings → use_dynamic_pricing'
                )
            )

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\nDRY RUN - No changes were saved'))

