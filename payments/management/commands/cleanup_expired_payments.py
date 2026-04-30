from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.payments.models import PendingPayment


class Command(BaseCommand):
    help = 'Cleanup expired PendingPayment records (older than 15 minutes)'

    def handle(self, *args, **options):
        expired = PendingPayment.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {count} expired pending payment(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No expired pending payments to clean up')
            )

