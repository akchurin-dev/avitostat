# celery.py

import os
from celery import Celery

# Устанавливаем переменную окружения для настройки Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')

# Создаем экземпляр Celery
app = Celery('avitostat')

# Загружаем конфигурацию из настроек Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем все задачи (tasks) из приложений Django
app.autodiscover_tasks()
