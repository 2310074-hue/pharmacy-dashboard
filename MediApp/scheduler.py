import os
import sys
import time
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from django.conf import settings

logger = logging.getLogger('MediApp.scheduler')

_scheduler_started = False
STATE_FILE = Path(settings.BASE_DIR) / 'daily_alert_state.json'


def get_ist_now():
    """Returns current datetime in Indian Standard Time (Asia/Kolkata)."""
    try:
        import zoneinfo
        ist_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        return datetime.now(ist_tz)
    except Exception:
        from django.utils import timezone
        return timezone.localtime(timezone.now())


def _get_last_sent_date():
    """Reads the last sent date string (YYYY-MM-DD) from persistent JSON state file."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_sent_date')
    except Exception as exc:
        logger.warning(f"Failed to read alert state file: {exc}")
    return None


def _save_last_sent_date(date_str):
    """Saves the last sent date string into persistent JSON state file."""
    try:
        data = {
            'last_sent_date': date_str,
            'updated_at': get_ist_now().strftime("%Y-%m-%d %I:%M:%S %p IST")
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.warning(f"Failed to write alert state file: {exc}")


def check_and_dispatch_daily_forecast_alert(force=False):
    """
    Checks if today's 8:00 AM IST restock alert has been sent.
    If not sent (and current IST hour >= 8 or force=True), dispatches email to admin.
    Returns result dict with status.
    """
    ist_now = get_ist_now()
    today_str = ist_now.date().isoformat()
    current_hour = ist_now.hour

    last_sent = _get_last_sent_date()

    if not force and last_sent == today_str:
        return {
            'success': True,
            'email_sent': False,
            'message': f'Daily AI Restock Alert for today ({today_str}) has already been sent to Admin.',
            'last_sent_date': last_sent,
            'current_ist_time': ist_now.strftime("%Y-%m-%d %I:%M %p IST")
        }

    if not force and current_hour < 8:
        return {
            'success': True,
            'email_sent': False,
            'message': f'Scheduled for 08:00 AM IST. Current time is {ist_now.strftime("%I:%M %p IST")}.',
            'last_sent_date': last_sent,
            'current_ist_time': ist_now.strftime("%Y-%m-%d %I:%M %p IST")
        }

    logger.info(f"⏰ Triggering Daily 8:00 AM IST AI Demand Restock Audit for {today_str} (IST Time: {ist_now.strftime('%I:%M %p')})...")

    from MediApp.forecasting import send_forecast_critical_stock_email
    result = send_forecast_critical_stock_email(force=True)

    if result.get('email_sent') or result.get('success'):
        _save_last_sent_date(today_str)
        logger.info(f"✅ Daily Restock Alert successfully dispatched to {result.get('recipient')} for {today_str}.")

    result['current_ist_time'] = ist_now.strftime("%Y-%m-%d %I:%M %p IST")
    result['last_sent_date'] = today_str
    return result


def _background_scheduler_loop():
    """
    Background daemon loop that executes daily automated AI demand & restock audits.
    Checks time in Indian Standard Time (IST) and dispatches alert once per day >= 8:00 AM IST.
    """
    logger.info("🟢 PharmaCare Daily 8:00 AM IST AI Restock Auto-Scheduler started.")

    # Small initial wait so Django database and apps finish loading
    time.sleep(10)

    # Initial check upon startup / wake-up
    try:
        check_and_dispatch_daily_forecast_alert(force=False)
    except Exception as exc:
        logger.error(f"❌ [Scheduler Init] Error on startup check: {exc}")

    while True:
        try:
            check_and_dispatch_daily_forecast_alert(force=False)
        except Exception as exc:
            logger.error(f"❌ [Scheduler Loop] Error during automated check: {exc}")

        # Sleep for 10 minutes before next check
        time.sleep(600)


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
    thread = threading.Thread(target=_background_scheduler_loop, daemon=True, name="PharmaCare-8AM-IST-Scheduler")
    thread.start()
    logger.info("🚀 PharmaCare Daily 8:00 AM IST Scheduler thread initialized.")
