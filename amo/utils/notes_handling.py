import json
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from celery import shared_task

import amo.models
from amo.utils import ai_answer_using
from amo.utils import amo_api
from amo.utils import amo_leads
from amo.utils import amo_messages
from amo.utils import chatbot_lead_pair_defining
from amo.utils import qualification
# from amo.utils.ai import answers
from amo.utils.ai import fields_recognition
from utils.logging import TraceLogger


class NoteAuthors(Enum):
    RIMZONA_RU = "Заявки с сайта rimzona.ru"
    RIMZONA_WHEELS = "rimzona-wheels.ru"


NOTE_AUTHORS_NAMES: set[str] = {note_author.value for note_author in NoteAuthors}


@dataclass
class FormParsed:
    auto_model: str | None
    diameter: str | None
    city: str | None


class BaseParser(ABC):
    @classmethod
    def parse(cls, text: str) -> FormParsed:
        lines = text.split("\n")
        return FormParsed(
            auto_model=cls.parse_auto_model(lines),
            diameter=cls.parse_diameter(lines),
            city=cls.parse_city(lines),
        )

    @classmethod
    @abstractmethod
    def parse_auto_model(cls, text_lines: list[str]) -> str | None:
        pass

    @classmethod
    @abstractmethod
    def parse_diameter(cls, text_lines: list[str]) -> str | None:
        pass

    @classmethod
    @abstractmethod
    def parse_city(cls, text_lines: list[str]) -> str | None:
        pass


class RimzonaRuParser(BaseParser):
    """
Марка, модель и год выпуска вашего авто
bmw 3 
Какой диаметр дисков вы выбираете?
R19
Из какого вы города?
москва 
Вам нужны шины?
Нет
    """

    @classmethod
    def parse_auto_model(cls, text_lines: list[str]) -> str | None:
        for i, line in enumerate(text_lines):
            if line == "Марка, модель и год выпуска вашего авто":
                return text_lines[i + 1]

        return None

    @classmethod
    def parse_diameter(cls, text_lines: list[str]) -> str | None:
        for i, line in enumerate(text_lines):
            if line == "Какой диаметр дисков вы выбираете?":
                return text_lines[i + 1].strip("RrРр ")

        return None

    @classmethod
    def parse_city(cls, text_lines: list[str]) -> str | None:
        for i, line in enumerate(text_lines):
            if line == "Из какого вы города?":
                return text_lines[i + 1]

        return None


class RimzonaWheelsParser(BaseParser):
    """
1) Напишите марку и модель вашего авто: митсубиши паджеро 
   
2) Какой диаметр дисков?: R15
3) Нужны ли вам шины?: Нет
4) Ваш город: Петропавловск-Каамчатский


Как связаться: WhatsApp
    """

    @classmethod
    def parse_auto_model(cls, text_lines: list[str]) -> str | None:
        for line in text_lines:
            if "Напишите марку и модель вашего авто" in line:
                return line.split(":")[-1].strip()

        return None

    @classmethod
    def parse_diameter(cls, text_lines: list[str]) -> str | None:
        for line in text_lines:
            if "Какой диаметр дисков?" in line:
                return line.split(":")[-1].strip("RrРр ")

        return None

    @classmethod
    def parse_city(cls, text_lines: list[str]) -> str | None:
        for line in text_lines:
            if "Ваш город" in line:
                return line.split(":")[-1].strip()

        return None


def handle_new_lead_note_webhook(request_data: dict, *, tlogger: TraceLogger) -> None:
    try:
        account_id = int(request_data["account[id]"])

        assert request_data["leads[note][0][note][element_type]"] == "2"
        lead_id = int(request_data["leads[note][0][note][element_id]"])

        note_type = int(request_data["leads[note][0][note][note_type]"])
        text = request_data["leads[note][0][note][text]"]

        metadata: dict = json.loads(request_data["leads[note][0][note][metadata]"])
        author_name = metadata["event_source"]["author_name"]
    except:
        tlogger.info("Error when parsing amo new lead note webhook request data")
        tlogger.info(request_data)
        raise

    handle_lead_note.s(
        account_id=account_id,
        lead_id=lead_id,
        note_type=note_type,
        author_name=author_name,
        text=text,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=30)


@shared_task
def handle_lead_note(
    account_id: int,
    lead_id: int,
    note_type: int,
    author_name: str,
    text: str,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    if note_type != 4:
        tlogger.info("Stop handling. Handle only notes with note_type = 4")
        return

    if author_name not in NOTE_AUTHORS_NAMES:
        tlogger.info(f"Stop handling. Note author is unknown, got '{author_name}'")
        return

    account = amo.models.AmoAccount.objects.get(amo_id=account_id)

    advised_lead = amo_api.get_lead(account, lead_id, tlogger=tlogger)
    assert advised_lead.contacts_ids
    contact_id = advised_lead.contacts_ids[0]

    chatbot_lead_pair = chatbot_lead_pair_defining.define_chatbot_and_lead(
        account=account,
        contact_id=contact_id,
        advised_lead_id=lead_id,
        tlogger=tlogger,
    )

    if chatbot_lead_pair is None:
        tlogger.info("Stop handling. Chatbot and lead aren't defined")
        return

    chatbot = chatbot_lead_pair.chatbot
    lead = chatbot_lead_pair.lead

    tlogger.info({
        "domain": account.domain,
        "chatbot": str(chatbot),
        "lead_id": lead.id,
        "pipeline_id": lead.pipeline_id,
        "status_id": lead.status_id,
        "contact_id": contact_id,
        "note_author_name": author_name,
        "text": text,
    })

    # ai_answer = answers.parse_form(account, chatbot, text, tlogger=tlogger)
    form = _parse_form(author_name, text)
    entities_fields_values: fields_recognition.EntitiesFieldsValues = {
        "lead": {
            "Марка модель год": form.auto_model,
            "Диаметр диска": form.diameter,
            "Город": form.city,
        },
        "contact": None,
    }

    contact = amo_leads.get_lead_contact(account, lead, tlogger=tlogger)
    if contact is None:
        tlogger.info("Stop handling. Contact is empty")
        return

    ai_answer_using.update_lead_and_contact(
        account=account,
        # ai_answer=ai_answer,
        entities_fields_values=entities_fields_values,
        lead=lead,
        contact=contact,
        tlogger=tlogger,
    )

    if not chatbot.message_when_note_received:
        tlogger.info("Don't send message. Message when note received is blank")
        return

    chat_id = amo_messages.create_chat_and_talk(account, contact, tlogger=tlogger)
    amo_api.send_message(
        account=account,
        chat_id=chat_id,
        text=chatbot.message_when_note_received,
        tlogger=tlogger,
    )

    qualification.change_status_if_qualification(chatbot, lead.id, tlogger=tlogger)


def _parse_form(note_author: str, text: str) -> FormParsed:
    author_to_parser: dict[str, type[BaseParser]] = {
        NoteAuthors.RIMZONA_RU.value: RimzonaRuParser,
        NoteAuthors.RIMZONA_WHEELS.value: RimzonaWheelsParser,
    }

    return author_to_parser[note_author].parse(text)
