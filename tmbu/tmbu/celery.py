import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tmbu.settings')

app = Celery('tmbu')

# Read config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks in all apps
app.autodiscover_tasks()