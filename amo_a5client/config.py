import datetime

from utils import increasing_delay


ORIGIN_NAME = "a5client"

RETRIES_DELAY_CONFIG = increasing_delay.IncreasingDelayConfig(
    first_delay=datetime.timedelta(seconds=5),
    multiplier=2,
    timeout=datetime.timedelta(minutes=10),
)
