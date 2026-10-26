import time
import requests
from pipelines.shared.time_units import utc_now
from .data import SOURCE


class ProviderRequestError(RuntimeError):
    def __init__(self,reason,status=None):
        self.reason=reason
        self.status=status
        super().__init__(f'RID request failed ({reason})')


def fetch(session=None,sleep=time.sleep):
    session=session or requests.Session()
    failure=ProviderRequestError('transport')
    for attempt in range(4):
        try:
            response=session.get(SOURCE,timeout=(10,40))
            if response.status_code==429 or response.status_code>=500:
                failure=ProviderRequestError('rate_limit' if response.status_code==429 else 'upstream',response.status_code)
                if attempt==3:
                    break
                wait=response.headers.get('Retry-After','')
                sleep(min(120,max(2**(attempt+1),int(wait) if wait.isdigit() else 0)))
                continue
            if response.status_code>=400:
                raise ProviderRequestError('http_permanent',response.status_code) from None
            try:
                payload=response.json()
            except ValueError:
                raise ProviderRequestError('invalid_json') from None
            return payload,utc_now()
        except requests.RequestException:
            failure=ProviderRequestError('transport')
            if attempt==3:
                break
            sleep(2**(attempt+1))
    raise failure from None
