import random
import time

from loguru import logger
import progress
import progress.bar
import progress.counter

from tests import config as global_config
from tests.utils.avito_utils import avito_accounts
from tests.utils.avito_utils import avito_chats


def write_message_from_client_account():
    # input("Отправьте с аккаунта клиента сообщение без контакта и без адреса...")
    phrases = [
        "что у вас продается",
        "почему не отвечаете",
        "давайте за 300, сегодня заберу",
        "у вас есть диски",
        "у вас продаются машины",
        "и что это значит",
    ]
    message = random.choice(phrases)
    avito_chats.send_message_from_client_account(message)
    logger.info("Client sent message without contacts and addreses")


def send_phone_number_from_client_account():
    # input("Отправьте номер телефона с аккаунта клиента...")
    phrases = [
        "мой номер 79925541133",
        "вацап 89913441133",
        "текстом свяжитесь 79441138833",
    ]
    message = random.choice(phrases)
    avito_chats.send_message_from_client_account(message)
    logger.info("Client sent phone number")


def send_address_from_client_account():
    # input("Отправьте адрес с аккаунта клиента...")
    phrases = [
        "я в москве метро университет",
        "пишу с саратова",
        "Волгоград улица ленина если что",
    ]
    message = random.choice(phrases)
    avito_chats.send_message_from_client_account(message)
    logger.info("Client sent address")


def write_message_from_seller_account():
    # input("Отправьте сообщение с аккаунта продавца...")
    message = "я менеджер, чем вам помочь"
    avito_chats.send_message_from_seller_account(message)
    logger.info("Seller sent message")


def wait_bot_handle_message(wait_sec: int = global_config.BOT_HANDLE_MESSAGE_WAIT_TIME_SEC):
    counter = progress.counter.Countdown("Wait bot handle message, left seconds ", max=wait_sec)

    for _ in range (wait_sec):
        time.sleep(1)
        counter.next()

    print()
