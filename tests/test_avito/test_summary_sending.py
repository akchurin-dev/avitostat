from tests.test_avito import utils as test_utils
from tests.test_avito.utils import avito_accounts
from tests.test_avito.utils import avito_chats
from tests.test_avito.utils import telegram as avito_telegram
from tests.utils import avitostat_test_api
from tests.utils import telegram


class TestSummarySending:
    @classmethod
    def setup_class(cls):
        cls.user_id = avitostat_test_api.create_user().id
        cls.avito_account, cls.avito_account_was_created = avito_accounts.get_or_create_avito_account(cls.user_id)
        avitostat_test_api.set_use_gpt_flag(True)

    @classmethod
    def teardown_class(cls):
        if cls.avito_account_was_created:
            avitostat_test_api.delete_avito_account(cls.avito_account.id)

        avitostat_test_api.delete_user(cls.user_id)

    def setup_method(self):
        avitostat_test_api.delete_avito_ai_chat_bot_by_avito_account(
            avito_account_id=self.avito_account.id,
            raise_on_404=False,
        )
        avitostat_test_api.create_avito_ai_chat_bot(
            avito_account_id=self.avito_account.id,
            turn_off_after_manager=False,
        )
        self.prev_session_last_msg = avito_chats.get_last_message_id_in_avito_chat()
        self.last_avito_msg = self.prev_session_last_msg
        self.last_tg_msg = telegram.get_last_message_id()
        avito_telegram.get_new_summaries(last_message_id=self.last_tg_msg)
        avitostat_test_api.set_prev_session_last_avito_message(self.prev_session_last_msg)

    def teardown_method(self):
        avitostat_test_api.delete_avito_ai_chat_bot_by_avito_account(
            avito_account_id=self.avito_account.id,
            raise_on_404=True,
        )
        avitostat_test_api.reset_prev_session_last_avito_message()

    def test_incoming_without_contacts(self):
        # Клиент пишет сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот не присылает отчет
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Клиент пишет сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот не присылает отчет
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]


    def test_incoming_with_contacts(self):
        # Клиент пишет сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Отчет не приходит
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )

        # Клиент отправляет контакты
        test_utils.send_phone_number_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отправил отчет
        self.last_tg_msg = avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=1,
        )[0].message_id

        # Бот ответил
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

    def test_incoming_with_address(self):
        # Клиент пишет сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Отчет не приходит
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Клиент присылает адрес
        test_utils.send_address_from_client_account()
        test_utils.wait_bot_handle_message()

        # Отчет приходит
        self.last_tg_msg = avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=1,
        )[0].message_id

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

    def test_a_few_incoming_with_contacts(self):
        # Клиент пишет сообщение
        test_utils.write_message_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Отчет не приходит
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )

        # Клиент присылает адрес
        test_utils.send_address_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Бот присылает отчет
        self.last_tg_msg = avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=1,
        )[0].message_id

        # Клиент присылает телефон
        test_utils.send_phone_number_from_client_account()
        test_utils.wait_bot_handle_message()

        # Бот отвечает
        self.last_avito_msg = avito_chats.check_new_outgoing_messages(
            last_message_id=self.last_avito_msg,
            new_messages_count=1,
        )[0]

        # Бот не присылает отчет
        avito_telegram.check_new_summaries(
            last_message_id=self.last_tg_msg,
            new_summaries_count=0,
        )
