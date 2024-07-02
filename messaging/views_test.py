from django.views import View
from aiogram import types, F
from telegram_bot import bot


class TelegramSenderTestView(View):
    def get(self, request):
        # sending a message directly
        bot.send_raw(chat_id="-1002061228822", text="TEST TEXT")
        # bot.send_raw('send_photo', chat_id=CHAT_ID, caption=TEXT, photo=URL)
