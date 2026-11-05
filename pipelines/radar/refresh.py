"""Cheap public readiness check before scheduled or recovery source capture."""
from datetime import datetime,timezone
import time
import requests

URL='https://hazard-intelligence-lime.vercel.app/api/radar'


def stamp(value):
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.timestamp() if parsed.utcoffset().total_seconds()==0 else None
    except (ValueError,TypeError,AttributeError):return None


def due_decision(value,now=None):
    now=time.time() if now is None else now
    health=value.get('health') or {};feed=value.get('feed') or {}
    frames=feed.get('frames') or []
    latest=stamp(frames[-1].get('observed_at')) if frames else None
    attempt=stamp(health.get('last_attempt'))
    # Allow the source time to advance; never alter observation or retrieval clocks.
    expected=int((now-12*60)//1800)*1800
    if latest is not None and latest<=now+300 and latest>=expected and health.get('status')=='SUCCESS':
        return {'due':False,'reason':'LATEST_SAMPLE_ALREADY_PUBLISHED'}
    if attempt is not None and 0<=now-attempt<600:
        return {'due':False,'reason':'RECENT_ATTEMPT_COOLDOWN'}
    return {'due':True,'reason':'MISSING_OR_OLDER_SAMPLE'}


def check_due(get=None,now=None):
    try:
        response=(get or requests.get)(URL,timeout=15,allow_redirects=False)
        if response.status_code!=200:raise ValueError('Readiness unavailable')
        return due_decision(response.json(),now)
    except (requests.RequestException,ValueError,TypeError,KeyError):
        return {'due':True,'reason':'PUBLIC_STATUS_UNAVAILABLE'}
