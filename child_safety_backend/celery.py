import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'child_safety_backend.settings')

app = Celery('child_safety_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
