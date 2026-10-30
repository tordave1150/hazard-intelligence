import json
import time
import requests
from pipelines.shared.time_units import utc_now
from .data import SOURCE


class ProviderRequestError(RuntimeError):
    def __init__(self,reason,status=None):self.reason=reason;self.status=status;super().__init__(reason)


def fetch(session=None,sleep=time.sleep):
    get=session.get if session is not None else requests.get
    for attempt in range(3):
        try:
            with get(SOURCE,timeout=(10,35),allow_redirects=False,stream=True,headers={'Accept':'application/json'}) as response:
                if response.status_code==429 or response.status_code>=500:
                    if attempt==2:raise ProviderRequestError('upstream_unavailable',response.status_code)
                    delay=response.headers.get('Retry-After','')
                    sleep(min(30,max(2**(attempt+1),int(delay) if delay.isdigit() else 0)));continue
                if response.status_code!=200:raise ProviderRequestError('http_error',response.status_code)
                parts=[];size=0;deadline=time.monotonic()+45
                for part in response.iter_content(65536):
                    size+=len(part)
                    if size>8*1024*1024 or time.monotonic()>deadline:raise ProviderRequestError('response_budget_exceeded')
                    parts.append(part)
                def reject(_):raise ValueError('Non-finite JSON')
                try:payload=json.loads(b''.join(parts).decode('utf-8-sig'),parse_constant=reject)
                except (ValueError,UnicodeDecodeError):raise ProviderRequestError('invalid_json') from None
                return payload,utc_now()
        except requests.RequestException:
            if attempt==2:raise ProviderRequestError('transport_error') from None
            sleep(2**(attempt+1))
    raise ProviderRequestError('transport_error')
