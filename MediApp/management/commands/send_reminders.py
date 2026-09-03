from django.core.management.base import BaseCommand
from django.utils import timezone
from MediApp.models import MedicineReminder
from MediApp.utils.email_utils import send_reminder_email

class Command(BaseCommand):
    help = 'Send due medicine reminders via email (run regularly via cron or scheduler).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate sending reminders without actually dispatching emails or updating database timestamps.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send all active reminders regardless of next_send timestamp.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        now = timezone.now()

        if dry_run:
            self.stdout.write(self.style.WARNING("=== Running in DRY-RUN mode ==="))

        if force:
            due = MedicineReminder.objects.all()
        else:
            due = MedicineReminder.objects.filter(next_send__lte=now)

        total_due = due.count()
        self.stdout.write(f"Found {total_due} reminder(s) eligible for sending.")

        if total_due == 0:
            self.stdout.write(self.style.SUCCESS("No reminders are currently due."))
            return

        sent_count = 0
        error_count = 0

        for r in due:
            customer = r.customer
            med_name = r.medicine.name if r.medicine else 'Medicine'
            self.stdout.write(f"Processing Reminder #{r.id} for customer: {customer.name} ({customer.email}) - Medicine: {med_name}")

            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"  [DRY-RUN] Would send email to {customer.email} for '{med_name}'"))
                sent_count += 1
                continue

            result = send_reminder_email(customer, r)
            if result['success']:
                sent_count += 1
                r.schedule_next(from_dt=now)
                if r.period == 'one_time':
                    r.next_send = None
                r.save()
                self.stdout.write(self.style.SUCCESS(f"  ✅ Email sent successfully to {customer.email}"))
            else:
                error_count += 1
                err_msg = result.get('error', 'Unknown error')
                self.stdout.write(self.style.ERROR(f"  ❌ Failed to send email to {customer.email}: {err_msg}"))

        self.stdout.write(self.style.SUCCESS(f"Finished processing. Sent: {sent_count}, Errors: {error_count}"))
