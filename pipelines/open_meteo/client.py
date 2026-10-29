import os
import time
import json
import requests
from pipelines.shared.time_units import utc_now
from .budget import active_budget, BudgetExceeded

DAILY = 'precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min'


class ProviderRequestError(RuntimeError):
    """Safe request diagnostics: never retain a response, URL, key or body."""
    def __init__(self, reason, status_code=None, retryable=True, transport_type=None):
        self.reason = reason
        self.status_code = status_code
        self.retryable = retryable
        self.transport_type = transport_type
        super().__init__(f'Open-Meteo {reason}' + (f' (HTTP {status_code})' if status_code is not None else ''))


def fetch_batch(locations, session=None, sleep=time.sleep):
    """One multi-coordinate request, with conservative bounded retries.

    API accounting still charges each coordinate; batching is not a quota bypass.
    No raw response or key is logged.
    """
    params = {'latitude': ','.join(str(x['lat']) for x in locations), 'longitude': ','.join(str(x['lon']) for x in locations),
              'daily': DAILY, 'timezone': 'Asia/Bangkok', 'forecast_days': 4}
    return _fetch(locations, params, session, sleep)


def fetch_hourly_batch(locations, day, session=None, sleep=time.sleep):
    from datetime import date, timedelta
    end = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    params = {'latitude': ','.join(str(x['lat']) for x in locations), 'longitude': ','.join(str(x['lon']) for x in locations),
              'hourly': 'precipitation,precipitation_probability,temperature_2m', 'timezone': 'Asia/Bangkok',
              'timeformat': 'unixtime', 'start_hour': day + 'T01:00', 'end_hour': end + 'T00:00'}
    return _fetch(locations, params, session, sleep)


def _fetch(locations, params, session, sleep):
    session = session or requests.Session()
    key = os.getenv('OPEN_METEO_API_KEY')
    url = 'https://customer-api.open-meteo.com/v1/forecast' if key else 'https://api.open-meteo.com/v1/forecast'
    if key:
        params['apikey'] = key
    for attempt in range(4):
        budget = active_budget.get()
        if budget is not None:
            try:
                budget.reserve(len(locations))
            except BudgetExceeded:
                raise ProviderRequestError('request_budget_exhausted', retryable=False) from None
        response = None
        try:
            response = session.get(url, params=params, timeout=(10, 60), allow_redirects=False, stream=True)
        except requests.RequestException as exc:
            failure = ProviderRequestError('transport_error', transport_type=type(exc).__name__)
        else:
            if not 200 <= response.status_code < 300 and hasattr(response, 'close'):
                response.close()
            if response.status_code == 429 or response.status_code >= 500:
                failure = ProviderRequestError('rate_limited' if response.status_code == 429 else 'upstream_unavailable', response.status_code)
            elif not 200 <= response.status_code < 300:
                raise ProviderRequestError('http_error', response.status_code, retryable=False) from None
            else:
                try:
                    if hasattr(response, 'iter_content'):
                        chunks, size, deadline = [], 0, time.monotonic() + 60
                        try:
                            for chunk in response.iter_content(65536):
                                size += len(chunk)
                                if size > 2 * 1024 * 1024 or time.monotonic() > deadline:
                                    raise ProviderRequestError('response_budget_exceeded', retryable=False)
                                chunks.append(chunk)
                            payload = json.loads(b''.join(chunks).decode('utf-8'))
                        finally:
                            response.close()
                    else:
                        payload = response.json() # In-memory test doubles; real HTTP is streamed above.
                except requests.RequestException as exc:
                    failure = ProviderRequestError('transport_error', transport_type=type(exc).__name__)
                except ValueError:
                    failure = ProviderRequestError('invalid_json')
                else:
                    payload = payload if isinstance(payload, list) else [payload]
                    if len(payload) != len(locations):
                        raise ValueError('Provider returned incomplete multi-location batch')
                    return payload, utc_now()
        if attempt == 3:
            raise failure from None
        retry_after = response.headers.get('Retry-After', '') if response is not None else ''
        sleep(min(120, max(2 ** (attempt + 1), int(retry_after) if retry_after.isdigit() else 0)))
    raise RuntimeError('Provider unavailable')
