from django.core.management.base import BaseCommand
from django.db import transaction
from apps.earnings.models import DriverEarningLedger
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Recover stuck PROCESSING earnings (legacy bug cleanup). Reverts earnings with status=PROCESSING, no stripe_transfer_id, and no payout_batch back to AVAILABLE.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be recovered without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('Checking for stuck PROCESSING earnings...'))
        
        # Find stuck earnings
        stuck_earnings = DriverEarningLedger.objects.filter(
            status='PROCESSING',
            stripe_transfer_id__isnull=True,
            payout_batch__isnull=True
        ).select_related('driver__user', 'trip')
        
        count = stuck_earnings.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No stuck earnings found. All good!'))
            return
        
        self.stdout.write(self.style.WARNING(f'Found {count} stuck earning(s):'))
        
        # Show details
        for earning in stuck_earnings[:10]:  # Show first 10
            self.stdout.write(
                f"  - Earning ID: {earning.id}, Driver: {earning.driver.id} "
                f"({earning.driver.user.email}), Trip: {earning.trip.id}, "
                f"Amount: {earning.net_amount} {earning.currency}, "
                f"Created: {earning.created_at}"
            )
        
        if count > 10:
            self.stdout.write(f"  ... and {count - 10} more")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN: No changes made. Use without --dry-run to recover.'))
            return
        
        # Recover them
        self.stdout.write(self.style.WARNING('\nRecovering stuck earnings...'))
        
        with transaction.atomic():
            recovered = stuck_earnings.update(status='AVAILABLE')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully recovered {recovered} earning(s). '
                f'Status changed from PROCESSING to AVAILABLE.'
            )
        )
        
        logger.info(f"Recovered {recovered} stuck PROCESSING earnings")

