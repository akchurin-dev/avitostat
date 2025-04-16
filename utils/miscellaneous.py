import datetime


def datetime_now_with_tz(utc_offset_hours: int) -> datetime.datetime:
    msk_tz = datetime.timezone(datetime.timedelta(hours=utc_offset_hours))
    msk_time_now = datetime.datetime.now(msk_tz)

    return msk_time_now
