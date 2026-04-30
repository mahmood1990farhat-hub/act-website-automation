"""
Management command to fix existing days_of_week data that was stored as strings.
This converts string values like "[0, 2]" or "'[0, 2]'" to proper JSON arrays.
Uses RAW SQL to bypass Django's JSONField issues with corrupted data.
Run this once to fix existing data.
"""
from django.core.management.base import BaseCommand
from django.db import connection
import json


class Command(BaseCommand):
    help = 'Fixes days_of_week data that was stored as strings instead of JSON arrays (one-time fix using raw SQL)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Checking for days_of_week data that needs fixing...'))
        
        # First, get all records using raw SQL to see the actual data
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, days_of_week::text FROM pricing_peaktimerule")
            rows = cursor.fetchall()
        
        if not rows:
            self.stdout.write(self.style.SUCCESS('No PeakTimeRule records found.'))
            return
        
        fixed_count = 0
        
        for row_id, name, days_value in rows:
            self.stdout.write(f'Checking rule {row_id}: "{name}" - raw value: {repr(days_value)}')
            
            # Check if it's a string that looks like a JSON array but with quotes
            needs_fix = False
            new_value = None
            
            if days_value is None:
                new_value = '[]'
                needs_fix = True
            elif isinstance(days_value, str):
                # Remove surrounding quotes if present
                cleaned = days_value.strip()
                
                # Check if it's wrapped in extra quotes like '"[0, 2]"' or "'[0, 2]'"
                if (cleaned.startswith('"') and cleaned.endswith('"')) or \
                   (cleaned.startswith("'") and cleaned.endswith("'")):
                    cleaned = cleaned[1:-1]
                    needs_fix = True
                
                # Try to parse as JSON
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        new_value = json.dumps(parsed)  # Re-serialize to ensure clean JSON
                        if new_value != days_value:
                            needs_fix = True
                    else:
                        new_value = '[]'
                        needs_fix = True
                except (json.JSONDecodeError, TypeError):
                    # Can't parse, set to empty list
                    new_value = '[]'
                    needs_fix = True
            
            if needs_fix and new_value is not None:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE pricing_peaktimerule SET days_of_week = %s::jsonb WHERE id = %s",
                            [new_value, row_id]
                        )
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Fixed rule {row_id}: "{name}" - set to {new_value}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Failed to fix rule {row_id}: "{name}" - {str(e)}'
                        )
                    )
            else:
                self.stdout.write(f'  - Rule {row_id}: OK')
        
        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('\nNo data needed fixing. All days_of_week values are properly formatted.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ Fixed {fixed_count} rule(s). All days_of_week values are now properly formatted as JSON arrays.')
            )

