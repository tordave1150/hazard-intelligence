"""Bounded HTTPS reachability receipts; no keys, forecast requests or response bodies."""
import json
import time
import requests


def main():
    for host in ('api.open-meteo.com','customer-api.open-meteo.com'):
        start=time.monotonic()
        try:
            with requests.get('https://'+host+'/',timeout=(10,15),allow_redirects=False,stream=True) as response:
                receipt={'host':host,'http_status':response.status_code}
        except requests.RequestException as exc:
            receipt={'host':host,'transport_type':type(exc).__name__}
        receipt['elapsed_seconds']=round(time.monotonic()-start,2)
        print(json.dumps(receipt),flush=True)


if __name__=='__main__':main()
