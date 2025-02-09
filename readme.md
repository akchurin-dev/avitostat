# Запуск вручную
source /var/www/avitostat/venv/bin/activate
cd /var/www/avitostat

gunicorn -c gunicorn_config.py base.wsgi:application

celery -A base worker -l info --pool=solo
celery -A base beat -l info
поверить очереди
celery -A base inspect active


# Почистить старые задачи 
    redis-cli flushall

# Освободить порт на маке
    lsof -i :8000
    kill -9 СВОЙ ПИД

убить гуникорн все процессы
ps aux | grep gunicorn | grep -v grep | awk '{print $2}' | xargs kill

htop - просмотрт системных ресурсов
ssh avitostata

логи в РЕАЛЬНОМ времени

sudo journalctl -u gunicorn.service -f
sudo journalctl -u celery-worker.service -f
sudo journalctl -u welcome_bot.service -f
sudo journalctl -u redis-server -f
sudo journalctl -u celery-beat.service -f

sudo systemctl stop  welcome_bot
sudo systemctl stop  gunicorn
sudo systemctl stop  celery-worker
sudo systemctl stop  celery-beat

РЕДИС НЕ ОСТАНАВЛИВАЕМ НИКОГДА, но если надо
redis-cli flushall


systemctl daemon-reload
sudo systemctl start welcome_bot
sudo systemctl start gunicorn
sudo systemctl start celery-worker
sudo systemctl start celery-beat

systemctl status welcome_bot.service
systemctl status gunicorn.service
systemctl status celery-worker.service
systemctl status celery-beat.service
systemctl status redis-server

логи последние (НЕ ОБНОВЛЯЮТСЯ В РЕАЛЬНОМ ВРЕМЕНИ)
sudo journalctl -u welcome_bot.service -e
sudo journalctl -u gunicorn.service -e
sudo journalctl -u redis-server -e
sudo journalctl -u celery-worker.service -e
sudo journalctl -u celery-beat.service -e


# CELERY
    Устанавливать надо селери и селери-бит локально (так проще на данном этапе)
# Запуск ВРУЧНУЮ
    celery -A base worker -l info --pool=solo
    celery -A base beat -l info

# Почистить старые задачи 
    redis-cli flushall

# Копирование базы

    sudo docker ps -a
    sudo docker stop 471abf4d3e44
    sudo docker rm 471abf4d3e44
    sudo docker-compose up -d
    python manage.py loaddata --exclude auth.permission --exclude contenttypes /Users/raufakchurin/projects/avitostat/db_backup.json
    ./manage.py runserver


# ОБЛАЧНАЯ БД

сделать бекап
PGPASSWORD='xxxxxx' pg_dump -h wokrofanu.beget.app -p 5432 -U cloud_user -d default_db -F c -f "local_db_dump_$(date +%Y-%m-%d).sql"
вводим пароль из учётки

подключение 
psql -h wokrofanu.beget.app -p 5432 -U cloud_user -d default_db
вводим пароль из учётки

 

восстановление БД из файла
psql -h wokrofanu.beget.app -p 5432 -U cloud_user -d default_db -f local_db_dump.sql
вводим пароль из учётки


# ОПИСАНИЕ СЕРВИСА
1)Сервис для сбора статистики с авито аккаунтов, расчет конверсии, полезных метрик, рассылка на телеграм аккаунты.
2)Анализ переписки менеджеров с клиентами, опции направленные на повышение конверсии когда это зависит от качества переписки.
Используя ИИ.

Планируется:
3)Централизация переписки в аккаунтах на один аккаунт телеграм(для того чтобы не прыгать по всем аккаунтам)

# Технические особенности реализации:
1) OAUTH2 avito  - доступ к множественным аккаунтам передаётся сервису посредством перехода по ссылке
2) Асинхронность везде где это имеет смысл+возможность релизовать, тк количетсво запросов может достигать 
200-300 для формирования одного отчёта когда в аккаунте к прмиеру 20000 объявлений
3) Sentry для удобного логирования ошибок
4) Селери - для создания рассылок отчетов по расписанию
5) Редис для создания очердей Селери
6) Рассылка отчётов в телеграм группы непосредственно из Джанго.(без аиограмм)
7) Облачная БД тк для тестовых прогонов необходимы рабочие токены авито
8) Система отслеживания успешности отправленных отчётов самописная
9) Джаго Джет для более приятного вида админки


# Поднятие ПОСТГРЕСС ЛОКАЛЬНО
1) скормить ГПТ докер-копоус и попросить инструкцию
2) docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' avitostata_db
данная команда показывает реальынй айпи адрес контейнера с БД
АЙПИ прописываем в конфиге джанго в АЛЛОВЕД-хостс, а так же в настройка подключения БД
3) Возможно атк же поможет
https://proghunter.ru/articles/django-base-2023-installing-postgresql-in-django

# Дропнуть БД в контейнере
docker exec -it avitostata_db sh
psql -U postgres -d template1
DROP DATABASE postgres;
CREATE DATABASE postgres;

./manage.py makemigrations
./manage.py migrate

[//]: # (./manage.py populate_db)
./manage.py runserver


# ОТКАТ МИГРАЦИЙ

-посмотреть названия миграций
python manage.py showmigrations

-указываем миграцию - которая должна стать текущей и название приложения сперва
python manage.py migrate avito_account 0003_workschedule



#  ПОЧИНИТЬ ЛОГАУТ в ДЖЕТ ДЖАНГО

файл venv/lib/python3.12/site-packages/django/contrib/auth/views.py
меняем
     http_method_names = ["post", "options"]
на   http_method_names = ["get", "options"]

меняем
        def post(self, request, *args, **kwargs):
на      def get(self, request, *args, **kwargs):


