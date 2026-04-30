from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myProject.settings')

app = Celery('myProject')

# Load config from settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks.py in all apps
app.autodiscover_tasks()
