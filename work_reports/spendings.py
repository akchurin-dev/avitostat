from datetime import datetime
from typing import NamedTuple

import ai_requests.models


class TokensCoast(NamedTuple):
    dollars_per_mil_input_tokens: float
    dollars_per_mil_output_tokens: float


MODELS_TO_COASTS: dict[str, TokensCoast] = {
    "gpt-4.1-2025-04-14": TokensCoast(2, 8),
    "gpt-4o-2024-08-06": TokensCoast(5, 20),
}


class Spending(NamedTuple):
    project_name: str
    spent_dollars: float


class Spendings:
    _spendings: list[Spending]
    _projects_to_spendings: dict[str, Spending]

    def __init__(self, spendings: list[Spending]) -> None:
        self._spendings = spendings
        self._projects_to_spendings = {spending.project_name: spending for spending in self._spendings}

    def get_project_spending(self, project: str) -> Spending:
        return self._projects_to_spendings.get(project, ZERO_SPENDING)

    def __iter__(self):
        for spending in self._spendings:
            yield spending


ZERO_SPENDING = Spending("PROJECT NOT FOUND", 0)


def get_spendings(since: datetime, until: datetime) -> Spendings:
    qs = ai_requests.models.AIRequest.objects.filter(
        created_at__range=(since, until),
        tag__isnull=False,
    )

    model_to_project_tokens_spending: dict[str, dict[str, tuple[float, float]]] = {}

    for ai_request in qs:
        if ai_request.model not in model_to_project_tokens_spending:
            model_to_project_tokens_spending[ai_request.model] = {}

        if ai_request.tag.count("|") != 2:
            continue

        project = ai_request.tag.split("|")[1].strip()
        tokens_spending = model_to_project_tokens_spending[ai_request.model].get(project, (0, 0))

        model_to_project_tokens_spending[ai_request.model][project] = (
            tokens_spending[0] + ai_request.tokens_prompt,
            tokens_spending[1] + ai_request.tokens_completion,
        )

    project_to_dollars_spending: dict[str, float] = {}

    for model in model_to_project_tokens_spending:
        tokens_coast = MODELS_TO_COASTS.get(model, TokensCoast(0, 0))
        for project, (tokens_prompt, tokens_completion) in model_to_project_tokens_spending[model].items():
            project_to_dollars_spending[project] = sum([
                project_to_dollars_spending.get(project, 0),
                tokens_prompt * tokens_coast.dollars_per_mil_input_tokens / 10 ** 6,
                tokens_completion * tokens_coast.dollars_per_mil_output_tokens / 10 ** 6
            ])

    return Spendings([Spending(project, spent_dollars) for project, spent_dollars in project_to_dollars_spending.items()])
