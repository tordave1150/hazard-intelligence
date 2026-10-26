import os
import time
import requests
from pipelines.shared.time_units import utc_now

DAILY = 'precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min'


class ProviderRequestError(RuntimeError):
    """Safe request diagnostics: never retain a response, URL, key or body."""
    def __init__(self, reason, status_code=None, retryable=True):
        self.reason = reason
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(f'Open-Meteo {reason}' + (f' (HTTP {status_code})' if status_code is not None else ''))


def fetch_batch(locations, session=None, sleep=time.sleep):
    """One multi-coordinate request, with conservative bounded retries.

    API accounting still charges each coordinate; batching is not a quota bypass.
    No raw response or key is logged.
    """
    session = session or requests.Session()
    key = os.getenv('OPEN_METEO_API_KEY')
    url = 'https://customer-api.open-meteo.com/v1/forecast' if key else 'https://api.open-meteo.com/v1/forecast'
    params = {'latitude': ','.join(str(x['lat']) for x in locations), 'longitude': ','.join(str(x['lon']) for x in locations),
              'daily': DAILY, 'timezone': 'Asia/Bangkok', 'forecast_days': 4}
    if key:
        params['apikey'] = key
    for attempt in range(4):
        response = None
        try:
            response = session.get(url, params=params, timeout=(10, 60))
        except requests.RequestException:
            failure = ProviderRequestError('transport_error')
        else:
            if response.status_code == 429 or response.status_code >= 500:
                failure = ProviderRequestError('rate_limited' if response.status_code == 429 else 'upstream_unavailable', response.status_code)
            elif not 200 <= response.status_code < 300:
                raise ProviderRequestError('http_error', response.status_code, retryable=False) from None
            else:
                try:
                    payload = response.json()
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
