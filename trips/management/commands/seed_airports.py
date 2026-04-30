from django.core.management.base import BaseCommand

from utils.demo_seed import seed_airports


class Command(BaseCommand):
    help = "Create or update sample UK airports with detection polygons (PostGIS)."

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
            seed_airports(self.stdout, self.style, dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True)
