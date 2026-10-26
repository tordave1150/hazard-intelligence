from datetime import datetime, timezone
from .time_units import instant


def freshness(reference_time, fetched_at, now=None):
    """Forecast age is bounded by its oldest valid period AND retrieval age.

    Daily Open-Meteo responses do not expose a reliable model issuance instant.
    An old forecast fetched again cannot be made fresh by retrieval alone.
    """
    if not reference_time or not fetched_at:
        return 'UNKNOWN'
    now = now or datetime.now(timezone.utc)
    age = max((now - instant(reference_time)).total_seconds(), (now - instant(fetched_at)).total_seconds()) / 3600
    if age < -1:
        return 'UNKNOWN'
    return 'FRESH' if age <= 30 else 'DELAYED' if age <= 48 else 'STALE'


def check_batch(records, expected_ids):
    expected = set(expected_ids)
    ids = [r['location_id'] for r in records]
    if not expected or len(ids) != len(set(ids)) or set(ids) != expected:
        raise ValueError('Incomplete, duplicate or unexpected location coverage; retaining last good snapshot')
    periods = [tuple(p['date'] for p in r['valid_periods']) for r in records]
    if len(set(periods)) != 1:
        raise ValueError('Mixed forecast periods; retaining last good snapshot')
    return {'requested_locations': len(expected), 'successful_locations': len(ids), 'missing_locations': [], 'completeness': 1.0}
