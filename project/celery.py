import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tadac.settings")

app = Celery("tadac")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
