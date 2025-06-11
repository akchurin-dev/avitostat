from typing import Iterable

from openai.types.responses import Response
from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseTextConfigParam
from openai.types.responses.easy_input_message_param import EasyInputMessageParam as GPTMessage
import pydantic

import amo.models
import messaging.api
import chat_bot.ai_utils
from ai_requests import ai_requests
from amo.utils import amo_ai
from amo.utils import amo_api
from amo.utils import amo_leads
from utils.logging import TraceLogger


def generate_answer(
    chatbot: amo.models.AmoChatBot,
    messages: list[messaging.api.ChatMessage],
    amo_account: amo.models.AmoAccount,
    lead_id: int,
    *,
    tlogger: TraceLogger,
) -> amo_ai.AIAnswer:

    if not chat_bot.ai_utils.use_gpt_flag():
        return amo_ai.AIAnswer.model_validate({})

    lead, contact = amo_leads.get_lead_contact_pair(chatbot.account, lead_id, tlogger=tlogger)
    all_fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot)
    unknown_fillable_fields = amo_ai.get_unknown_fillable_fields(all_fillable_fields, lead, contact)
    available_pipeline_statuses = amo_api.get_pipeline_statuses(amo_account, lead.pipeline_id, tlogger=tlogger)

    gpt_messages = _get_gpt_messages(
        chatbot=chatbot,
        messages=messages,
        all_fillable_fields=all_fillable_fields,
        unknown_fillable_fields=unknown_fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        lead=lead,
        contact=contact,
    )

    text_format = amo_ai.get_text_format(
        chatbot=chatbot,
        fields=unknown_fillable_fields,
        field_for_answer=True,
        available_pipeline_statuses=available_pipeline_statuses,
        tlogger=tlogger,
    )

    error = None

    for _ in range(amo_ai.AI_RETRIES):
        try:
            response = chat_bot.ai_utils.client.responses.create(
                model=chat_bot.ai_utils.MODEL,
                input=gpt_messages,
                text=text_format,
                max_output_tokens=2000,
            )
            ai_requests.create_from_response(response, tlogger=tlogger)

            payload = amo_ai.AIAnswerPayload.model_validate_json(response.output_text)

            break
        except pydantic.ValidationError as e:
            error = e
            tlogger.info({
                "title": "Invalid gpt response",
                "error": e,
            })
    else:
        if error:
            raise error

    return amo_ai.get_ai_answer_wrapper(response, payload, tlogger=tlogger)


def _get_gpt_messages(
    chatbot: amo.models.AmoChatBot,
    messages: list[messaging.api.ChatMessage],
    # transcriptions: TranscriptionsForMessages,
    all_fillable_fields: Iterable[amo.models.FillableField],
    unknown_fillable_fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    lead: amo_api.Lead,
    contact: amo_api.Contact,
) -> ResponseInputParam:

    current_status = None

    for status in available_pipeline_statuses:
        if status.id == lead.status_id:
            current_status = status
            break

    if current_status is None:
        raise Exception(f"Status (id={lead.status_id}) not found in pipeline (id={lead.pipeline_id})")

    prompt = amo_ai.get_prompt(chatbot, unknown_fillable_fields, available_pipeline_statuses, current_status)

    gpt_messages: ResponseInputParam = [{"role": "system", "content": prompt}]

    if chatbot.duplicate_instructions:
        gpt_messages.append({"role": "user", "content": chatbot.duplicate_instructions})

    lead_contact_info = amo_ai.known_lead_contact_info(all_fillable_fields, lead, contact)
    if lead_contact_info:
        gpt_messages.append({"role": "user", "content": lead_contact_info})

    gpt_messages.extend([chat_bot.ai_utils.avito_message_to_gpt_format(message) for message in messages])

    return gpt_messages
