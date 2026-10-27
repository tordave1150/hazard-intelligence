import time
import requests
from pipelines.shared.time_units import utc_now
from .data import SOURCE,allowed_document
from .transform import feed_index,normalize,make_feed


class ProviderRequestError(RuntimeError):
    def __init__(self,reason,status=None,document_id=None):
        self.reason=reason;self.status=status;self.document_id=document_id
        super().__init__(f'TMD request failed ({reason})')


def request(url,session,sleep=time.sleep,deadline=None):
    if url!=SOURCE and not allowed_document(url):raise ValueError('Unapproved TMD URL')
    document_id='rss_index' if url==SOURCE else url.rsplit('/CAP',1)[-1][:-4]
    # Only a bounded ID from an already-allowlisted public CAP URL is logged.
    if len(document_id)>128:document_id='cap_document'
    error=lambda reason,status=None:ProviderRequestError(reason,status,document_id)
    failure=error('transport')
    def remaining():
        left=deadline-time.monotonic() if deadline is not None else 600
        if left<=0:raise error('collection_deadline')
        return left
    def pause(seconds):
        if seconds>=remaining():raise error('collection_deadline')
        sleep(seconds)
    for attempt in range(4):
        try:
            left=remaining()
            with session.get(url,timeout=(min(10,left),min(30,left)),allow_redirects=False,stream=True) as response:
                status=response.status_code
                if status==429 or status>=500:
                    failure=error('rate_limit' if status==429 else 'upstream',status)
                    delay=response.headers.get('Retry-After','')
                elif status!=200:raise error('http_permanent',status) from None
                else:
                    body=bytearray()
                    for chunk in response.iter_content(65536):
                        remaining()
                        body.extend(chunk)
                        if len(body)>2*1024*1024:raise error('oversized_response')
                    remaining();return bytes(body),utc_now()
            if attempt<3:pause(min(120,max(2**(attempt+1),int(delay) if delay.isdigit() else 0)))
        except requests.RequestException:
            failure=error('transport')
            if attempt<3:pause(2**(attempt+1))
    raise failure from None


def collect(session=None,sleep=time.sleep):
    session=session or requests.Session()
    deadline=time.monotonic()+300
    raw,_=request(SOURCE,session,sleep,deadline);items,generated=feed_index(raw)
    records=[];ignored=0;size=len(raw)
    for item in items:
        if time.monotonic()>=deadline:raise ProviderRequestError('collection_deadline')
        sleep(1)
        raw,fetched=request(item['url'],session,sleep,deadline);size+=len(raw)
        if size>4*1024*1024:raise ProviderRequestError('feed_size_bound')
        row=normalize(raw,item['url'],fetched)
        if row is None:ignored+=1
        else:records.append(row)
    if time.monotonic()>=deadline:raise ProviderRequestError('collection_deadline')
    return make_feed(items,generated,records,utc_now(),ignored)
