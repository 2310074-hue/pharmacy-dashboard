import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from MediApp.models import MedicineReminder
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class Command(BaseCommand):
    help = 'Dispatches SMS notifications for due medicine reminders'

    def handle(self, *args, **options):
        # Fetch Twilio credentials from environment variables
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_phone = os.environ.get('TWILIO_PHONE_NUMBER')
        
        # Determine if we are in mock mode
        mock_mode = not (account_sid and auth_token and from_phone)
        client = None
        
        if mock_mode:
            self.stdout.write(self.style.WARNING(
                "Twilio credentials not found in environment variables. "
                "Running in MOCK mode. SMS messages will be printed to the console."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("Twilio credentials found. Running in LIVE mode."))
            client = Client(account_sid, auth_token)

        now = timezone.now()
        
        # Find reminders where next_send is in the past or exactly now
        due_reminders = MedicineReminder.objects.filter(next_send__lte=now)
        
        if not due_reminders.exists():
            self.stdout.write("No reminders are currently due.")
            return

        count = 0
        for reminder in due_reminders:
            customer = reminder.customer
            medicine = reminder.medicine
            period = reminder.get_period_display().lower()
            
            med_name = medicine.name if medicine else "your medicine"
            
            # Personalize the message
            message_body = (
                f"Hello {customer.name}, this is a reminder from PharmaCare. "
                f"It's time for your {period} refill of {med_name}. "
                f"{reminder.reminder_text}"
            )
            
            # Send SMS
            to_phone = customer.contact_number
            # Clean phone number (add +91 for India if missing, assume international format is needed for Twilio)
            if to_phone and not to_phone.startswith('+'):
                to_phone = f"+91{to_phone}" # Defaulting to India country code for example
                
            if mock_mode:
                self.stdout.write("-" * 40)
                self.stdout.write(self.style.MIGRATE_HEADING(f"MOCK SMS to {to_phone}:"))
                self.stdout.write(message_body)
                self.stdout.write("-" * 40)
            else:
                try:
                    message = client.messages.create(
                        body=message_body,
                        from_=from_phone,
                        to=to_phone
                    )
                    self.stdout.write(self.style.SUCCESS(f"Sent SMS to {to_phone} (SID: {message.sid})"))
                except TwilioRestException as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send SMS to {to_phone}: {e}"))
            
            # Schedule the next send
            reminder.schedule_next(from_dt=now)
            reminder.save()
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f"Successfully processed {count} reminders."))
