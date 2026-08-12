import datetime
import sys
from dataclasses import dataclass


@dataclass
class IncreasingDelayConfig:
    first_delay: datetime.timedelta
    multiplier: float
    timeout: datetime.timedelta


Delay = int | float | datetime.timedelta


def next_delay(reduced_delay: Delay, config: IncreasingDelayConfig) -> datetime.timedelta:
    reduced_delay_td: datetime.timedelta | None = None

    if isinstance(reduced_delay, (float, int)):
        reduced_delay_td = datetime.timedelta(seconds=reduced_delay)

    if isinstance(reduced_delay, datetime.timedelta):
        reduced_delay_td = reduced_delay

    if reduced_delay_td is None:
        return _raise_unsupportable_type_for_delay(reduced_delay)

    new_delay = config.first_delay

    if reduced_delay_td.total_seconds() > sys.float_info.epsilon:
        new_delay = reduced_delay_td * config.multiplier

    return new_delay


def is_timeout(reduced_delay: Delay, config: IncreasingDelayConfig) -> bool:
    if isinstance(reduced_delay, (float, int)):
        return reduced_delay >= config.timeout.total_seconds()

    if isinstance(reduced_delay, datetime.timedelta):
        return reduced_delay >= config.timeout

    return _raise_unsupportable_type_for_delay(reduced_delay)


def _raise_unsupportable_type_for_delay(value):
    raise ValueError(F"Unsupportable type for delay, got {type(value)}")
