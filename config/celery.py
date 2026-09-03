import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab
app.conf.beat_schedule = {
    'send-expiry-reminders-daily-9am': {
        'task': 'MediApp.tasks.send_expiry_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
}
