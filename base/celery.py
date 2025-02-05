import os
import logging
from celery import Celery

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Устанавливаем переменную окружения для настройки Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')

# Создаем экземпляр Celery
celery_app = Celery('avitostat')

# Загружаем конфигурацию из настроек Django
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем все задачи (tasks) из приложений Django
celery_app.autodiscover_tasks()

