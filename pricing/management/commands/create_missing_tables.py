"""
Management command to create missing pricing tables.
This is a one-time fix for migration issues where some tables exist but others don't.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from decimal import Decimal


class Command(BaseCommand):
    help = 'Creates missing pricing tables that should exist from 0001_initial migration'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Checking for missing pricing tables...'))
        
        with connection.cursor() as cursor:
            # Check which tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'pricing_%'
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            self.stdout.write(f'Existing pricing tables: {existing_tables}')
            
            # Tables that should exist from 0001_initial
            required_tables = {
                'pricing_pricingsettings',
                'pricing_pricingtier',
                'pricing_peaktimerule',
                'pricing_airportfee'
            }
            
            missing_tables = required_tables - existing_tables
            
            if not missing_tables:
                self.stdout.write(self.style.SUCCESS('All pricing tables exist!'))
                return
            
            self.stdout.write(self.style.WARNING(f'Missing tables: {missing_tables}'))
            
            # Create PricingTier table if missing
            if 'pricing_pricingtier' in missing_tables:
                self.stdout.write('Creating pricing_pricingtier table...')
                cursor.execute("""
                    CREATE TABLE pricing_pricingtier (
                        id BIGSERIAL NOT NULL PRIMARY KEY,
                        min_distance_miles NUMERIC(6, 2) NOT NULL,
                        max_distance_miles NUMERIC(6, 2) NOT NULL,
                        rate_per_mile NUMERIC(10, 2) NOT NULL,
                        "order" INTEGER NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        vehicle_type_id BIGINT NOT NULL REFERENCES vehicle_vehicletype(id) DEFERRABLE INITIALLY DEFERRED
                    );
                """)
                cursor.execute("""
                    CREATE INDEX pricing_pri_vehicle_4c6b34_idx ON pricing_pricingtier(vehicle_type_id, min_distance_miles);
                """)
                cursor.execute("""
                    ALTER TABLE pricing_pricingtier 
                    ADD CONSTRAINT pricing_tier_max_gt_min_distance 
                    CHECK (max_distance_miles > min_distance_miles);
                """)
                cursor.execute("""
                    CREATE UNIQUE INDEX pricing_pricingtier_vehicle_type_id_min_distance_miles_max_distance_miles_uniq 
                    ON pricing_pricingtier(vehicle_type_id, min_distance_miles, max_distance_miles);
                """)
                self.stdout.write(self.style.SUCCESS('  ✓ Created pricing_pricingtier'))
            
            # Create PeakTimeRule table if missing
            if 'pricing_peaktimerule' in missing_tables:
                self.stdout.write('Creating pricing_peaktimerule table...')
                cursor.execute("""
                    CREATE TABLE pricing_peaktimerule (
                        id BIGSERIAL NOT NULL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        days_of_week JSONB NOT NULL DEFAULT '[]',
                        multiplier NUMERIC(5, 3) NOT NULL DEFAULT 1.0,
                        priority INTEGER NOT NULL DEFAULT 0,
                        vehicle_type_id BIGINT REFERENCES vehicle_vehicletype(id) DEFERRABLE INITIALLY DEFERRED
                    );
                """)
                cursor.execute("""
                    CREATE INDEX pricing_pea_is_acti_6c0cc6_idx ON pricing_peaktimerule(is_active, priority);
                """)
                cursor.execute("""
                    CREATE INDEX pricing_pea_vehicle_1b4927_idx ON pricing_peaktimerule(vehicle_type_id, is_active);
                """)
                self.stdout.write(self.style.SUCCESS('  ✓ Created pricing_peaktimerule'))
            
            # Create AirportFee table if missing
            if 'pricing_airportfee' in missing_tables:
                self.stdout.write('Creating pricing_airportfee table...')
                cursor.execute("""
                    CREATE TABLE pricing_airportfee (
                        id BIGSERIAL NOT NULL PRIMARY KEY,
                        pickup_fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                        dropoff_fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                        airport_id BIGINT NOT NULL REFERENCES trips_airport(id) DEFERRABLE INITIALLY DEFERRED,
                        vehicle_type_id BIGINT NOT NULL REFERENCES vehicle_vehicletype(id) DEFERRABLE INITIALLY DEFERRED
                    );
                """)
                cursor.execute("""
                    CREATE UNIQUE INDEX pricing_airportfee_airport_id_vehicle_type_id_uniq 
                    ON pricing_airportfee(airport_id, vehicle_type_id);
                """)
                self.stdout.write(self.style.SUCCESS('  ✓ Created pricing_airportfee'))
            
            connection.commit()
            self.stdout.write(self.style.SUCCESS('\n✓ All missing tables created successfully!'))

