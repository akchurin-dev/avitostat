import os
import logging
from celery import Celery
from celery.signals import task_failure

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Устанавливаем переменную окружения для настройки Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')

# Создаем экземпляр Celery
celery_app = Celery('avitostat')

# Загружаем конфигурацию из настроек Django
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем все задачи (tasks) из приложений Django
celery_app.autodiscover_tasks()


#ROLLBAR SETTINGS
# if os.environ.get('CELERY_WORKER_RUNNING') == '1':
#     from django.conf import settings
#     import rollbar
#     rollbar.init(**settings.ROLLBAR)
#
#     def celery_base_data_hook(request, data):
#         data['framework'] = 'celery'
#
#     rollbar.BASE_DATA_HOOK = celery_base_data_hook
#
#     @task_failure.connect
#     def handle_task_failure(**kw):
#         rollbar.report_exc_info(extra_data=kw)

