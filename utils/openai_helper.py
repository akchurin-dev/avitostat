import pydantic
from openai import NOT_GIVEN
from openai import NotGiven
from openai import OpenAI
from openai.types.responses import Response
from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseTextConfigParam

from ai_requests import ai_requests
from base import settings
from utils.logging import TraceLogger


AI_RETRIES = 3
MODEL = "gpt-4.1-2025-04-14"

client = OpenAI(api_key=settings.OPENAI_SECRET_KEY)


def openai_request(
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


def openai_parse_request(
    input: ResponseInputParam,
    text_format: type[pydantic.BaseModel],
    max_output_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> Response:

    error = None

    for _ in range(AI_RETRIES):
        try:
            response = client.responses.parse(
                model=MODEL,
                input=input,
                text_format=text_format,
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
