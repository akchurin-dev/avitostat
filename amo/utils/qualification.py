import amo.models
from amo.utils import amo_api
from amo.utils import amo_leads
from utils.logging import TraceLogger


def change_status_if_qualification(
    chatbot: amo.models.AmoChatBot,
    lead_id: int,
    contact_id: int,
    *,
    tlogger: TraceLogger,
) -> bool:

    lead = amo_api.get_lead(chatbot.account, lead_id, tlogger=tlogger)

    if not should_check_qualification(chatbot, lead, tlogger=tlogger):
        return False

    contact = amo_api.get_contact(chatbot.account, contact_id, tlogger=tlogger)

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

    fields_name_value = {
        "lead": {},
        "contact": {},
    }

    if lead.custom_fields_values:
        fields_name_value["lead"] = {
            field_value.field_name: field_value.values[0].value for field_value in lead.custom_fields_values
        }

    if contact.custom_fields_values:
        fields_name_value["contact"] = {
            field_value.field_name: field_value.values[0].value for field_value in contact.custom_fields_values
        }

    for field in fields_for_qualification:
        value = None

        if field.entity == amo.models.AmoEntity.LEAD:
            value = fields_name_value["lead"].get(field.name)

        if field.entity == amo.models.AmoEntity.CONTACT:
            value = fields_name_value["contact"].get(field.name)

        if value is None:
            tlogger.info(f"Qualification isn't achieved. {field.entity}.{field.name} isn't filled")
            return False

        tlogger.info({"qulification field filled": {
            "field": field.name,
            "value": value,
        }})

    tlogger.info("Qualification is achieved")
    return True
