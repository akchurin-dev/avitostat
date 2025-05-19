import datetime
import re


def datetime_now_with_tz(utc_offset_hours: int) -> datetime.datetime:
    msk_tz = datetime.timezone(datetime.timedelta(hours=utc_offset_hours))
    msk_time_now = datetime.datetime.now(msk_tz)

    return msk_time_now


PHONE_NUMBER_PATTERN = re.compile(r"\d+\s*\(?(\s*\d){3,}\s*\)?\s*-?(\s*\d){3,}\s*-?(\s*\d){2,}\s*-?(\s*\d){2,}")


def find_phone_number_in_chat(messages: list[str]) -> list[str]:
    matches: list[str] = []

    for msg in messages:
        match = PHONE_NUMBER_PATTERN.match(msg)

        if match:
            matches.append(match.group(0))

    return matches
