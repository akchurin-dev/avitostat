import pydantic
from openai import NOT_GIVEN
from openai import NotGiven
from openai.types.responses import Response
from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseTextConfigParam

from ai_requests import ai_requests
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import client
from utils.logging import TraceLogger


AI_RETRIES = 3


def openai_request_with_retries(
    input: ResponseInputParam,
    text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
    max_output_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> Response:

    error = None

    for _ in range(AI_RETRIES):
        try:
            response = client.responses.create(
                model=MODEL,
                input=input,
                text=text,
                max_output_tokens=max_output_tokens,
            )
            ai_requests.create_from_response(tag, response, tlogger=tlogger)
            return response
        except pydantic.ValidationError as e:
            error = e
            tlogger.info({
                "title": "Invalid gpt response",
                "error": e,
            })

    assert error
    raise error
