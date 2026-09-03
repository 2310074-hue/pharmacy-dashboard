from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from datetime import timedelta

from .models import Batch, SaleItem, Customer, ReminderLog, ExpiryReminderLog


@shared_task(bind=True)
def send_expiry_reminders(self):
    today = timezone.now().date()
    cutoff = today + timedelta(days=7)
    batches = Batch.objects.filter(expiry_date__gte=today, expiry_date__lte=cutoff, quantity__gt=0, reminder_sent=False)
    sent = 0
    for batch in batches:
        # use helper to send and log
        result = send_reminders_for_batch(batch)
        if result.get('sent_count', 0) > 0:
            sent += result['sent_count']

    return {'sent': sent}


@shared_task
def send_reminder_to_customer(batch_id, customer_email):
    try:
        batch = Batch.objects.get(id=batch_id)
    except Batch.DoesNotExist:
        return {'error': 'batch not found'}
    med = batch.medicine
    # send single reminder using helper
    context = {'customer_name': '', 'medicine_name': med.name, 'expiry_date': batch.expiry_date}
    text_content = render_to_string('email/medicine_expiry_reminder.txt', context)
    html_content = render_to_string('email/medicine_expiry_reminder.html', context)
    try:
        msg = EmailMultiAlternatives('Medicine Expiry Reminder', text_content, settings.DEFAULT_FROM_EMAIL, [customer_email])
        msg.attach_alternative(html_content, 'text/html')
        msg.send(fail_silently=False)
        # log to both ReminderLog and ExpiryReminderLog
        ReminderLog.objects.create(medicine_name=med.name, customer_email=customer_email, sent_at=timezone.now(), success=True, message=html_content)
        ExpiryReminderLog.objects.create(customer_email=customer_email, customer_name='', medicine_name=med.name, expiry_date=batch.expiry_date, reminder_sent=True, sent_at=timezone.now(), message=html_content)
        # set batch flag
        batch.reminder_sent = True
        batch.save()
        return {'sent': True}
    except Exception as e:
        ReminderLog.objects.create(medicine_name=med.name, customer_email=customer_email, sent_at=timezone.now(), success=False, message=str(e))
        ExpiryReminderLog.objects.create(customer_email=customer_email, customer_name='', medicine_name=med.name, expiry_date=batch.expiry_date, reminder_sent=False, message=str(e))
        return {'sent': False, 'error': str(e)}


def send_reminders_for_batch(batch):
    """Send reminders for a batch to recent purchasers and permanent customers.
    Returns dict with sent_count and errors.
    """
    med = batch.medicine
    one_year_ago = timezone.now() - timedelta(days=365)
    customers = {}
    sale_items = SaleItem.objects.filter(medicine=med, sale__date__gte=one_year_ago).select_related('sale__customer')
    for si in sale_items:
        c = si.sale.customer if si.sale else None
        if c and c.email:
            customers[c.email] = c.name
    perm_customers = Customer.objects.filter(is_permanent=True)
    for c in perm_customers:
        if c.email:
            customers[c.email] = c.name

    sent_count = 0
    errors = []
    for email, name in customers.items():
        subject = 'Medicine Expiry Reminder'
        context = {'customer_name': name or 'Customer', 'medicine_name': med.name, 'expiry_date': batch.expiry_date}
        text_content = render_to_string('email/medicine_expiry_reminder.txt', context)
        html_content = render_to_string('email/medicine_expiry_reminder.html', context)
        try:
            msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
            msg.attach_alternative(html_content, 'text/html')
            msg.send(fail_silently=False)
            ReminderLog.objects.create(medicine_name=med.name, customer_email=email, sent_at=timezone.now(), success=True, message=html_content)
            ExpiryReminderLog.objects.create(customer_email=email, customer_name=name or '', medicine_name=med.name, expiry_date=batch.expiry_date, reminder_sent=True, sent_at=timezone.now(), message=html_content)
            sent_count += 1
        except Exception as e:
            ReminderLog.objects.create(medicine_name=med.name, customer_email=email, sent_at=timezone.now(), success=False, message=str(e))
            ExpiryReminderLog.objects.create(customer_email=email, customer_name=name or '', medicine_name=med.name, expiry_date=batch.expiry_date, reminder_sent=False, message=str(e))
            errors.append(str(e))

    if sent_count > 0:
        batch.reminder_sent = True
        batch.save()

    return {'sent_count': sent_count, 'errors': errors}
