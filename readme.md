# ОПИСАНИЕ СЕРВИСА
1)Сервис для сбора статистики с авито аккаунтов, расчет конверсии, полезных метрик, рассылка на телеграм аккаунты.
2)Анализ переписки менеджеров с клиентами, опции направленные на повышение конверсии когда это зависит от качества переписки.
Используя ИИ.

Планируется:
3)Централизация переписки в аккаунтах на один аккаунт телеграм(для того чтобы не прыгать по всем аккаунтам)

# Технические особенности реализации:
1) OAUTH2 avito  - доступ к аккаунтам передаётся сервису посредством перехода по ссылке клиентом и подтвеждения.
2) Асинхронность, тк количетсво запросов может достигать 200-300 для формирования одного отчёта когда в аккаунте к прмиеру 
20000 объявлений
3) Sentry для удобного логирования ошибок
4) Селери - для создания рассылок отчетов по расписанию
5) Редис для создания очердей Селери
6) Рассылка отчётов в телеграм группы непосредственно из Селери.(без аиограмм)






# Поднятие ПОСТГРЕСС ЛОКАЛЬНО
1) скормить ГПТ докер-копоус и попросить инструкцию
2) docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' avitostata_db
данная команда показывает реальынй айпи адрес контейнера с БД
АЙПИ прописываем в конфиге джанго в АЛЛОВЕД-хостс, а так же в настройка подключения БД
3) Возможно атк же поможет
https://proghunter.ru/articles/django-base-2023-installing-postgresql-in-django


source /var/www/avitostat/venv/bin/activate
cd /var/www/avitostat

gunicorn -c gunicorn_config.py base.wsgi:application
убить гуникорн все процессы
ps aux | grep gunicorn | grep -v grep | awk '{print $2}' | xargs kill

htop - просмотрт системных ресурсов

ssh avitostata

systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl start aiogram
sudo systemctl start celery-worker
sudo systemctl start celery-beat

sudo systemctl stop  gunicorn
sudo systemctl stop  aiogram
sudo systemctl stop  celery-worker
sudo systemctl stop  celery-beat

systemctl status gunicorn.service
systemctl status aiogram.service
systemctl status celery-worker.service
systemctl status celery-beat.service

логи 
sudo journalctl -u aiogram.service
sudo journalctl -u gunicorn.service
sudo journalctl -u celery-worker.service
sudo journalctl -u celery-beat.service


#тут все конфиги системктл
cd /etc/systemd/system/ 




# Конфиг для бота

[Unit]
Description=Aiogram bot

[Service]
Type=simple
WorkingDirectory=/var/www/avitostat
ExecStart=/var/www/avitostat/venv/bin/python3 /var/www/avitostat/bot.py
KillMode=process
Restart=always
RestartSec=10
EnvironmentFile=/var/www/avitostat/.env

[Install]
WantedBy=multi-user.target


# КОнфиг для джанго 

[Unit]
Description=Django
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/avitostat
ExecStart=/var/www/avitostat/venv/bin/gunicorn -c gunicorn_config.py base.wsgi:application
KillMode=process
Restart=always
RestartSec=10
EnvironmentFile=/var/www/avitostat/.env

[Install]
WantedBy=multi-user.target



# CELERY
    Устанавливать надо селери и селери-бит локально (так проще на данном этапе)

# Запуск ВРУЧНУЮ
    celery -A base worker -l info
    celery -A base beat -l info

# Запуск 


# Конфиги СЕЛЕРИ для системктл

# Конфиг для воркера
[Unit]
Description=Celery Worker Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/avitostat
ExecStart=/var/www/avitostat/venv/bin/celery -A base worker -l info
Restart=always
RestartSec=10
EnvironmentFile=/var/www/avitostat/.env
KillMode=process


# Конфиг для бита

[Install]
WantedBy=multi-user.target

[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/var/www/avitostat
ExecStart=/var/www/avitostat/venv/bin/celery -A base beat -l info
Restart=always
RestartSec=10
EnvironmentFile=/var/www/avitostat/.env
KillMode=process

[Install]
WantedBy=multi-user.target


# Копирование базы

    sudo docker ps -a
    sudo docker stop 471abf4d3e44
    sudo docker rm 471abf4d3e44
    sudo docker-compose up -d
    python manage.py loaddata --exclude auth.permission --exclude contenttypes /home/rauf/PycharmProjects/avitostat/data.json
    ./manage.py runserver
