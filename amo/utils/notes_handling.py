from utils.logging import TraceLogger


def handle_new_lead_note_webhook(request_data: dict, *, tlogger: TraceLogger) -> None:
    try:
        account_id = int(request_data["account[id]"])
        note: dict = request_data["leads[note][0][note]"]

        entity_type: str | None = note.get("element_type")
        lead_id: int | None = None
        if entity_type == "2":
            lead_id = note["element_id"]
    except:
        tlogger.info("Error when parsing amo new lead note webhook request data")
        tlogger.info(request_data)
        raise
