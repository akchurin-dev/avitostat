import pprint

from tests import config as global_config
from tests.test_avito.utils import avito_chats


class Config:
    def __init__(self) -> None:
        self._seller_access_token: str | None = None
        self._seller_refresh_token: str | None = None
        self._avito_chat_id = global_config.AVITO_CHAT_ID

    @property
    def summary_chat_id(self) -> int:
        if global_config.SUMMARY_CHAT_ID is None:
            raise Exception("telegram_id is empty")

        return global_config.SUMMARY_CHAT_ID

    @property
    def avito_chat_id(self) -> str:
        while self._avito_chat_id is None:
            chats = {
                chat.id: {
                    "users": chat.users_name,
                    "last_message": chat.last_message_text,
                } for chat in avito_chats.get_chats(limit=3)
            }
            print()
            pprint.pprint(chats)

            self._avito_chat_id = input("Введите id тестового чата: ")
            if avito_chats.get_chat_info(self._avito_chat_id) is not None:
                break

        return self._avito_chat_id

    @property
    def seller_access_token(self) -> str:
        if not self._seller_access_token:
            self._seller_access_token = input("Введите авито access-токен продавца: ")

        return self._seller_access_token

    @seller_access_token.setter
    def seller_access_token(self, value: str):
        self._seller_access_token = value

    @property
    def seller_refresh_token(self) -> str:
        if not self._seller_refresh_token:
            self._seller_refresh_token = input("Введите авито refresh-токен продавца: ")

        return self._seller_refresh_token

    @seller_refresh_token.setter
    def seller_refresh_token(self, value: str):
        self._seller_refresh_token = value

    @property
    def seller_avito_account_id(self) -> int:
        if not global_config.SELLER_AVITO_ACCOUNT_ID:
            raise Exception("There isn't TEST_SELLER_AVITO_ACCOUNT_ID in environment variables")

        return global_config.SELLER_AVITO_ACCOUNT_ID


config = Config()
