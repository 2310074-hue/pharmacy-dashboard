from django.apps import AppConfig


class MediappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'MediApp'

    def ready(self):
        try:
            from .scheduler import start_auto_forecast_alert_scheduler
            start_auto_forecast_alert_scheduler()
        except Exception:
            pass
