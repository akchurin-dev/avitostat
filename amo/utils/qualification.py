import amo.models
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils import amo_leads
from utils.logging import TraceLogger


def change_status_if_qualification(
    chatbot: amo.models.AmoChatBot,
    lead_id: int,
    *,
    tlogger: TraceLogger,
) -> bool:

    lead, contact = amo_leads.get_lead_contact_pair(chatbot.account, lead_id, tlogger=tlogger)

    if not should_check_qualification(chatbot, lead, tlogger=tlogger):
        return False

    if not qualification_achieved(chatbot.pk, lead, contact, tlogger=tlogger):
        return False

    assert chatbot.new_status_when_qualification
    amo_leads.change_lead_status(
        account=chatbot.account,
        lead_id=lead.id,
        status_id=chatbot.new_status_when_qualification.amo_id,
        tlogger=tlogger,
    )

    return True


def should_check_qualification(chatbot: amo.models.AmoChatBot, lead: amo_api.Lead, *, tlogger: TraceLogger) -> bool:
    if chatbot.new_status_when_qualification is None:
        tlogger.info("Don't check qualification. new_status_when_qualification is null")
        return False

    pipeline_statuses_to_chatbot = amo.models.AmoPipelineStatusChatbotLink.objects.filter(
        chatbot=chatbot,
        check_qualification=True,
    ).select_related("status")

    if len(pipeline_statuses_to_chatbot) == 0:
        tlogger.info("Don't check qualification. Bot doesn't have status on which qulification is checked")
        return False

    for pipeline_status_to_chatbot in pipeline_statuses_to_chatbot:
        if pipeline_status_to_chatbot.status.amo_id == lead.status_id:
            return True

    tlogger.info("Don't check qualification. Current status isn't qulification checking status")
    return False


def qualification_achieved(chatbot_id: int, lead: amo_api.Lead, contact: amo_api.Contact, *, tlogger: TraceLogger) -> bool:
    fields_for_qualification = amo.models.FillableField.objects.filter(
        chatbot_id=chatbot_id,
        required_for_qualification=True,
    )

    fields_name_value: dict[str, dict[str, amo_api.CustomFieldValue]] = {
        "lead": {},
        "contact": {},
    }

    if lead.custom_fields_values:
        fields_name_value["lead"] = {
            field_value.field_name: field_value for field_value in lead.custom_fields_values
        }

    if contact.custom_fields_values:
        fields_name_value["contact"] = {
            field_value.field_name: field_value for field_value in contact.custom_fields_values
        }

    for field in fields_for_qualification:
        field_value = None

        if field.entity == amo.models.AmoEntity.LEAD:
            field_value = fields_name_value["lead"].get(field.name)

        if field.entity == amo.models.AmoEntity.CONTACT:
            field_value = fields_name_value["contact"].get(field.name)

        if field_value is None:
            _log_about_qualification_not_achieved(field, tlogger)
            return False

        if not amo_fields.field_filled(field_value):
            _log_about_qualification_not_achieved(field, tlogger)
            return False

        tlogger.info({"qulification field filled": {
            "field": field.name,
            "values": [value.value for value in field_value.values],
        }})

    tlogger.info("Qualification is achieved")
    return True


def _log_about_qualification_not_achieved(field: amo.models.FillableField, tlogger: TraceLogger) -> None:
    tlogger.info(f"Qualification isn't achieved. {field.entity}.{field.name} isn't filled")
