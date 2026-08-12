import datetime
import re


def datetime_now_msk():
    return datetime_now_with_tz(utc_offset_hours=3)


def datetime_now_with_tz(utc_offset_hours: int) -> datetime.datetime:
    utc_time_now = datetime.datetime.now(datetime.timezone.utc)
    return datetime_from_utc_to_tz(utc_time_now, utc_offset_hours)


def datetime_from_utc_to_tz(dt: datetime.datetime, utc_offset_hours: int) -> datetime.datetime:
    tz = get_tz(utc_offset_hours)    
    return dt.astimezone(tz)


def get_tz(utc_offset_hours: int) -> datetime.timezone:
    return datetime.timezone(datetime.timedelta(hours=utc_offset_hours))


PHONE_NUMBER_PATTERN = re.compile(r"^(\d*\D+)*\+?\s*\d?\s*\(?(\s*\d){3}\s*\)?\s*-?(\s*\d){3}(\s*-?(\s*\d){2}){2}(\D+\d*)*$")


def find_phone_numbers_in_chat(messages: list[str]) -> list[str]:
    matches: list[str] = []

    for msg in messages:
        match = PHONE_NUMBER_PATTERN.search(msg)

        if match:
            matches.append(match.group(0))

    return matches
