import pprint
import random
import string
from typing import Callable

from loguru import logger


class TraceLogger:
    def __init__(self, trace_id: str | None = None) -> None:
        self.trace_id = trace_id or new_trace_id()

    def info(self, msg) -> None:
        self._log(logger.info, msg)

    def warning(self, msg) -> None:
        self._log(logger.warning, msg)

    def error(self, msg) -> None:
        self._log(logger.error, msg)

    def _log(self, log_method: Callable[[str], None], msg) -> None:
        if not isinstance(msg, str):
            msg = pprint.pformat(msg)

        log_method(f"trace({self.trace_id}): {msg}")


def new_trace_id() -> str:
    TRACE_LENGTH = 20
    SYMBOLS = string.ascii_letters + string.digits

    return "".join([random.choice(SYMBOLS) for _ in range(TRACE_LENGTH)])
