import os
import sys
import time
import logging
import threading
from datetime import datetime, date
from django.utils import timezone

logger = logging.getLogger('MediApp.scheduler')

_scheduler_started = False
_last_auto_sent_date = None


def _background_scheduler_loop():
    """
    Background daemon loop that executes daily automated AI demand & restock audits.
    Dispatches alert emails to admin once per day automatically without manual clicks.
    """
    global _last_auto_sent_date
    logger.info("🟢 PharmaCare Daily AI Restock Auto-Scheduler thread started.")

    # Small initial sleep on startup so Django fully initializes all apps & models
    time.sleep(15)

    while True:
        try:
            now = timezone.now()
            today_date = now.date()

            # Trigger condition: If not sent today and hour is >= 8 AM (or on startup if after 8 AM)
            if _last_auto_sent_date != today_date and now.hour >= 8:
                logger.info(f"⏰ [Auto-Scheduler] Triggering daily AI Demand Restock Audit for {today_date}...")
                
                from MediApp.forecasting import send_forecast_critical_stock_email
                result = send_forecast_critical_stock_email(force=False)

                if result.get('email_sent'):
                    logger.info(f"✅ [Auto-Scheduler] Daily alert email successfully sent: {result.get('message')}")
                else:
                    logger.info(f"ℹ️ [Auto-Scheduler] Audit complete: {result.get('message')}")

                _last_auto_sent_date = today_date
        except Exception as exc:
            logger.error(f"❌ [Auto-Scheduler] Error during automated restock check: {exc}")

        # Sleep for 15 minutes before next periodic check
        time.sleep(900)


def start_auto_forecast_alert_scheduler():
    """
    Starts the automatic daily forecasting scheduler daemon thread.
    Prevents duplicate threads during Django's auto-reloader by checking RUN_MAIN or process flags.
    """
    global _scheduler_started
    if _scheduler_started:
        return

    # Check if running under management commands like migrate, makemigrations, collectstatic
    commands_to_skip = {'makemigrations', 'migrate', 'collectstatic', 'check', 'test', 'shell'}
    if any(cmd in sys.argv for cmd in commands_to_skip):
        return

    # For runserver, only start in the main process (RUN_MAIN == 'true')
    is_runserver = 'runserver' in sys.argv
    if is_runserver and os.environ.get('RUN_MAIN') != 'true':
        return

    _scheduler_started = True
    thread = threading.Thread(target=_background_scheduler_loop, daemon=True, name="PharmaCare-Daily-AI-Scheduler")
    thread.start()
    logger.info("🚀 PharmaCare Background Daily AI Alert Scheduler initialized successfully.")
