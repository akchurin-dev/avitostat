import os
from celery import Celery

# Устанавливаем переменную окружения для настройки Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')

# Создаем экземпляр Celery
celery_app = Celery('avitostat')

# Загружаем конфигурацию из настроек Django
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем все задачи (tasks) из приложений Django
celery_app.autodiscover_tasks()


# Определяем периодические задачи
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Пример периодической задачи, которая запускается каждые 10 секунд
    sender.add_periodic_task(10.0, test.s('hello'), name='add every 10 seconds')


@celery_app.task
def test(arg):
    print(arg)
