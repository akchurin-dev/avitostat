from celery import shared_task
from telegram_bot import bot

@shared_task
def send_test_message():
    bot.send_raw(chat_id="-1002061228822", text="TEST TEXT")