"""
Management command: send_stock_notifications

Finds all medicines with stock > 0 and sends a stock-availability email
to all permanent customers. Suitable for scheduled/cron execution.

Usage:
    python manage.py send_stock_notifications
    python manage.py send_stock_notifications --medicine-id 5   # notify for a specific medicine
"""

from django.core.management.base import BaseCommand, CommandError
from MediApp.models import Medicine, Customer
from MediApp.utils.email_utils import send_stock_available_email


class Command(BaseCommand):
    help = 'Send stock-availability notifications to all permanent customers for medicines that are in stock.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--medicine-id',
            type=int,
            default=None,
            help='Notify for a specific medicine ID only (optional). Defaults to all in-stock medicines.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Print what would be sent without actually sending emails.',
        )

    def handle(self, *args, **options):
        medicine_id = options['medicine_id']
        dry_run = options['dry_run']

        # Fetch medicines
        if medicine_id:
            try:
                medicines = [Medicine.objects.get(id=medicine_id)]
            except Medicine.DoesNotExist:
                raise CommandError(f'Medicine with ID {medicine_id} does not exist.')
        else:
            # Only medicines that have stock
            all_medicines = Medicine.objects.prefetch_related('batches').all()
            medicines = [m for m in all_medicines if m.total_quantity > 0]

        if not medicines:
            self.stdout.write(self.style.WARNING('No in-stock medicines found. Nothing to send.'))
            return

        # Fetch permanent customers
        permanent_customers = list(Customer.objects.filter(is_permanent=True).exclude(email=''))
        if not permanent_customers:
            self.stdout.write(self.style.WARNING(
                'No permanent customers found. Mark customers as permanent first via the dashboard.'
            ))
            return

        self.stdout.write(
            f'Found {len(medicines)} medicine(s) and {len(permanent_customers)} permanent customer(s).'
        )

        total_sent = 0
        total_errors = []

        for medicine in medicines:
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[DRY RUN] Would send "{medicine.name}" notification to {len(permanent_customers)} customer(s).'
                    )
                )
                continue

            self.stdout.write(f'Sending notifications for "{medicine.name}" ({medicine.total_quantity} units)...')
            result = send_stock_available_email(medicine, permanent_customers)
            total_sent += result['sent']
            if result['errors']:
                total_errors.extend(result['errors'])
                for err in result['errors']:
                    self.stdout.write(self.style.WARNING(f'  ⚠ {err}'))
            self.stdout.write(
                self.style.SUCCESS(f'  ✅ Sent to {result["sent"]} customer(s).')
            )

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone! Total emails sent: {total_sent}. Total errors: {len(total_errors)}.'
            ))
