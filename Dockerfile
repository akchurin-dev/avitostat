FROM python:3.10.17-slim-bullseye

WORKDIR /var/www/avitostat

COPY . .

RUN python3 -m pip install -r requirements.txt
