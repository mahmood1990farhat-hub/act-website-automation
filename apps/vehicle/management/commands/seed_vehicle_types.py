from django.core.management.base import BaseCommand

from utils.demo_seed import seed_vehicle_types


class Command(BaseCommand):
    help = "Create or update VehicleType rows for each key in utils.calculate_cost.PRICING."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print actions only; roll back in a wrapping transaction.",
        )

    def handle(self, *args, **options):
        from django.db import transaction

        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes persisted."))
        with transaction.atomic():
            seed_vehicle_types(self.stdout, self.style, dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True)
