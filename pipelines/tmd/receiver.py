"""Publish geometry qualifications only after the compatible reader is live."""
import time
import requests


def wait_for_receiver(get=None,sleep=None):
    get=get or requests.get;sleep=sleep or time.sleep
    for attempt in range(72):
        try:
            r=get('https://hazard-intelligence-lime.vercel.app/api/warnings',timeout=10)
            if r.status_code==200 and r.json().get('geometry_protocol')=='tmd-cap-geometry-v1':return
        except (requests.RequestException,ValueError):pass
        if attempt==71:raise RuntimeError('Compatible CAP receiver not ready')
        sleep(5)
