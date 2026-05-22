"""Celery application bootstrap for NeuraForge AI."""
import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("neuraforge")
# Read config from Django settings, namespaced with CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")
# Auto-discover tasks.py in every installed app.
app.autodiscover_tasks()


@setup_logging.connect
def configure_logging(*args, **kwargs):  # pragma: no cover
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


@app.task(bind=True, ignore_result=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
