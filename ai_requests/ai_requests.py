from openai.types.responses import Response as OpenaiResponse
from openai.types.chat import ChatCompletion as OpenaiCompletion

from ai_requests.models import AIRequest
from utils.logging import TraceLogger
from utils.yandex_gpt_api import CompletionResult as YandexGPTCompletion


def create_from_openai_response(tag: str, response: OpenaiResponse, *, tlogger: TraceLogger) -> AIRequest:
    tokens_completion = tokens_prompt = 0

    completion_detail: str = ""
    prompt_detail: str = ""

    if response.usage:
        tokens_completion = response.usage.output_tokens
        tokens_prompt = response.usage.input_tokens
        completion_detail = str(response.usage.output_tokens_details)
        prompt_detail = str(response.usage.input_tokens_details)

    return create(
        tag=tag,
        model=response.model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
        tlogger=tlogger,
    )


def create_from_openai_completion(tag: str, completion: OpenaiCompletion, *, tlogger: TraceLogger) -> AIRequest:
    tokens_completion = tokens_prompt = 0

    completion_detail: str = ""
    prompt_detail: str = ""

    if completion.usage:
        tokens_completion = completion.usage.completion_tokens
        tokens_prompt = completion.usage.prompt_tokens
        completion_detail = str(completion.usage.completion_tokens_details)
        prompt_detail = str(completion.usage.prompt_tokens_details)

    return create(
        tag=tag,
        model=completion.model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
        tlogger=tlogger,
    )


def create_from_yandex_gpt_completion(tag: str, model: str, completion: YandexGPTCompletion, *, tlogger: TraceLogger) -> AIRequest:
    return create(
        tag=tag,
        model=model,
        tokens_completion=completion.usage.completion_tokens,
        tokens_prompt=completion.usage.input_text_tokens,
        completion_detail=str(completion.usage.completion_tokens_details),
        prompt_detail="",
        tlogger=tlogger,
    )


def create(
    tag: str,
    model: str,
    tokens_completion: int,
    tokens_prompt: int,
    completion_detail: str = "",
    prompt_detail: str = "",
    *,
    tlogger: TraceLogger,
) -> AIRequest:

    msg = f"Request to gpt '{model}': " + "; ".join(k + "=" + str(v) for k, v in [
        ("tokens_completion", tokens_completion),
        ("tokens_prompt", tokens_prompt),
        ("completion_detail", completion_detail),
        ("prompt_detail", prompt_detail),
        ("tag", tag),
    ])
    tlogger.info(msg)

    return AIRequest.objects.create(
        tag=tag,
        model=model,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
        completion_detail=completion_detail,
        prompt_detail=prompt_detail,
    )
