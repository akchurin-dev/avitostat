#тут все конфиги системктл
cd /etc/systemd/system/ 

# Конфиг для welcome бота

[Unit]
Description=welcome bot

[Service]
Type=simple
WorkingDirectory=/var/www/avitostat/welcome_bot
ExecStart=/var/www/avitostat/venv/bin/python3 /var/www/avitostat/welcome_bot/bot.py
KillMode=process
Restart=always
RestartSec=10
EnvironmentFile=/var/www/avitostat/.env

[Install]
WantedBy=multi-user.target

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