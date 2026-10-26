from datetime import datetime, timezone, timedelta

BANGKOK = timezone(timedelta(hours=7))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return result.astimezone(timezone.utc)


def daily_period(day):
    start = datetime.fromisoformat(day).replace(tzinfo=BANGKOK)
    end = start + timedelta(days=1)
    return tuple(x.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z') for x in (start, end))
