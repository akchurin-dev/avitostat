from tests.config import avito_config
from tests.utils import avitostat_test_api
from tests.utils import avito_utils as test_utils
from tests.utils.avito_utils import avito_accounts
from tests.utils.avito_utils import avito_chats


class TestTurnOffAfterManagerFlag:
    @classmethod
    def setup_class(cls):
        cls.user_id = avitostat_test_api.create_user().id
        cls.avito_account, cls.avito_account_was_created = avito_accounts.get_or_create_avito_account(cls.user_id)
        avitostat_test_api.set_use_gpt_flag(False)

    @classmethod
    def teardown_class(cls):
        if cls.avito_account_was_created:
            avitostat_test_api.delete_avito_account(cls.avito_account.id)

        avitostat_test_api.delete_user(cls.user_id)

    def setup_method(self):
        avitostat_test_api.delete_avito_ai_chat_bot_by_avito_account(self.avito_account.id, raise_on_404=False)
        self.prev_session_last_message_id = avito_chats.get_last_message_id_in_avito_chat()
        self.last_avito_msg = self.prev_session_last_message_id
        avitostat_test_api.set_prev_session_last_avito_message(self.prev_session_last_message_id)

    def teardown_method(self):
        avitostat_test_api.delete_avito_chat_bot_tasks(avito_chat_id=avito_config.config.avito_chat_id)
        avitostat_test_api.delete_avito_ai_chat_bot(ai_chat_bot_id=self.aichatbot.id)

    def test_turn_off_after_manager_enabled(self):
        self.aichatbot = avitostat_test_api.create_avito_ai_chat_bot(self.avito_account.id, turn_off_after_manager=True)
        avitostat_test_api.reset_prev_session_last_avito_message()
        
        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()

        # Менеджер отвечает
        test_utils.write_message_from_seller_account()
        test_utils.wait_bot_handle_message()

        # Бот не отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1, # Сообщение от менеджера
        )[0]

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот не отвечает
        avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=0,
        )

    def test_turn_off_after_manager_disabled(self):
        self.aichatbot = avitostat_test_api.create_avito_ai_chat_bot(self.avito_account.id, turn_off_after_manager=False)

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()

        # Менеджер отвечает
        test_utils.write_message_from_seller_account()
        test_utils.wait_bot_handle_message()

        # Бот не отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1, # Сообщение менеджера
        )[0]

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )

    def test_bot_dont_turn_off_after_itself_when_turn_off_after_manager_enabled(self):
        self.aichatbot = avitostat_test_api.create_avito_ai_chat_bot(self.avito_account.id, turn_off_after_manager=True)

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

    def test_incoming_outgoing_incoming_when_turn_off_after_manager_enabled(self):
        self.aichatbot = avitostat_test_api.create_avito_ai_chat_bot(self.avito_account.id, turn_off_after_manager=True)

        # Клиент присылает сообщение
        # Не ждем пока сообщение обработается
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message(wait_sec=1)

        # Менеджер отвечает
        # Не ждем пока сообщение обработается
        self.last_avito_msg = test_utils.write_message_from_seller_account()
        test_utils.wait_bot_handle_message(wait_sec=1)

        # Клиент присылает сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Из исходящих только сообщение менеджера
        avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=0,
        )
