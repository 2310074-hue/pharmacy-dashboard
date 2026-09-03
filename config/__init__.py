from .celery import app as celery_app

# Expose the celery app as `celery_app` so that Django's autodiscover can find tasks.
