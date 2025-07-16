#!/bin/bash

# Остановка сервисов
echo "Stopping services..."
sudo systemctl stop welcome_bot
sudo systemctl stop gunicorn
sudo systemctl stop celery-worker
sudo systemctl stop celery-beat

# Перезагрузка systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Запуск сервисов
echo "Starting services..."
sudo systemctl start welcome_bot
sudo systemctl start gunicorn
sudo systemctl start celery-worker
sudo systemctl start celery-beat

echo "All services restarted successfully."
