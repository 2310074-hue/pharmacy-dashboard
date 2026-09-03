from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import timedelta

from MediApp.models import Batch, ExpiryReminderLog, Customer, SaleItem


class Command(BaseCommand):
    help = 'Send expiry reminders for batches expiring within next 7 days'

    def handle(self, *args, **options):
        today = timezone.now().date()
        cutoff = today + timedelta(days=7)
        batches = Batch.objects.filter(expiry_date__gte=today, expiry_date__lte=cutoff, quantity__gt=0)
        sent_count = 0

        for batch in batches:
            med = batch.medicine
            # find customers who bought this medicine in last year
            one_year_ago = timezone.now() - timedelta(days=365)
            customers = set()
            sale_items = SaleItem.objects.filter(medicine=med, sale__date__gte=one_year_ago)
            for si in sale_items:
                if si.sale and si.sale.customer and si.sale.customer.email:
                    customers.add((si.sale.customer.email, si.sale.customer.name))

            # also include permanent customers
            perm_customers = Customer.objects.filter(is_permanent=True)
            for c in perm_customers:
                if c.email:
                    customers.add((c.email, c.name))

            # send email to each customer
            for email, name in customers:
                subject = 'Medicine Expiry Reminder'
                context = {
                    'customer_name': name or 'Customer',
                    'medicine_name': med.name,
                    'expiry_date': batch.expiry_date,
                }
                message = render_to_string('email/medicine_expiry_reminder.txt', context)
                try:
                    html_content = render_to_string('email/medicine_expiry_reminder.html', context)
                    text_content = message
                    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=False)
                    log = ExpiryReminderLog.objects.create(
                        customer_email=email,
                        customer_name=name or '',
                        medicine_name=med.name,
                        expiry_date=batch.expiry_date,
                        reminder_sent=True,
                        sent_at=timezone.now(),
                        message=text_content,
                    )
                    sent_count += 1
                except Exception as e:
                    ExpiryReminderLog.objects.create(
                        customer_email=email,
                        customer_name=name or '',
                        medicine_name=med.name,
                        expiry_date=batch.expiry_date,
                        reminder_sent=False,
                        message=str(e),
                    )
        self.stdout.write(self.style.SUCCESS(f'Sent {sent_count} expiry reminders'))
