from openai.types.responses import Response
from openai.types.chat import ChatCompletion

from ai_requests.models import AIRequest
from utils.logging import TraceLogger


def create_from_response(response: Response, *, tlogger: TraceLogger) -> AIRequest:
    tokens_completion = tokens_prompt = 0

    completion_detail: str = ""
    prompt_detail: str = ""

    if response.usage:
        tokens_completion = response.usage.output_tokens
        tokens_prompt = response.usage.input_tokens
        completion_detail = str(response.usage.output_tokens_details)
        prompt_detail = str(response.usage.input_tokens_details)

    return create(
        model=response.model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
        tlogger=tlogger,
    )


def create_from_chat_completion(completion: ChatCompletion, *, tlogger: TraceLogger) -> AIRequest:
    tokens_completion = tokens_prompt = 0

    completion_detail: str = ""
    prompt_detail: str = ""

    if completion.usage:
        tokens_completion = completion.usage.completion_tokens
        tokens_prompt = completion.usage.prompt_tokens
        completion_detail = str(completion.usage.completion_tokens_details)
        prompt_detail = str(completion.usage.prompt_tokens_details)

    return create(
        model=completion.model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
        tlogger=tlogger,
    )


def create(
    model: str,
    tokens_completion: int,
    tokens_prompt: int,
    completion_detail: str = "",
    prompt_detail: str = "",
    *,
    tlogger: TraceLogger,
) -> AIRequest:

    tlogger.info(
        f"Request to gpt '{model}': "
        f"tokens_completion={tokens_completion}; "
        f"tokens_prompt={tokens_prompt}; "
        f"completion_detailt={completion_detail}; "
        f"prompt_detail={prompt_detail}"
    )

    return AIRequest.objects.create(
        model=model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
    )
