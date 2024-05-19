# Поднятие ПОСТГРЕСС ЛОКАЛЬНО

1) скормить ГПТ докер-копоус и попросить инструкцию
2) docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' avitostata_db
данная команда показывает реальынй айпи адрес контейнера с БД
АЙПИ прописываем в конфиге джанго в АЛЛОВЕД-хостс, а так же в настройка подключения БД
3) Возможно атк же поможет
https://proghunter.ru/articles/django-base-2023-installing-postgresql-in-django



ssh avitostata

systemctl daemon-reload
sudo systemctl start gunicorn
systemctl status gunicorn.service
