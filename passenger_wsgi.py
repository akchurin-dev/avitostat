# -*- coding: utf-8 -*-
import os, sys

sys.path.insert(0, '/var/www/avitostat')
sys.path.insert(1, '/var/www/avitostat/venv/lib/python3.10/site-packages/django/__init__.py')
os.environ['DJANGO_SETTINGS_MODULE'] = 'base.settings'
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
