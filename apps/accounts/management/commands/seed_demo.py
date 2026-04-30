from django.core.management.base import BaseCommand

from utils.demo_seed import run_seed


class Command(BaseCommand):
    help = (
        "Seed demo data: vehicle types (from PRICING), airports, demo users, "
        "a normal driver with vehicle, and optional sample trips."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run inside a transaction and roll back (no DB writes).",
        )
        parser.add_argument(
            "--no-trips",
            action="store_true",
            help="Skip sample Trip rows.",
        )
        parser.add_argument(
            "--with-pricing",
            action="store_true",
            help="Also run the existing seed_pricing_data command after seeding.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes will persist."))

        run_seed(
            self.stdout,
            self.style,
            dry_run=dry_run,
            with_trips=not options["no_trips"],
            with_pricing_command=options["with_pricing"],
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run finished (rolled back)."))
