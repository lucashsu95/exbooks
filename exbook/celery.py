import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exbook.settings")

app = Celery("exbook")
app.config_from_object("exbook.celery_config")
app.autodiscover_tasks()
