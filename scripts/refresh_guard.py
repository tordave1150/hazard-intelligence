"""Read-only due check for frequent, best-effort scheduler ticks.

Skipped ticks never change source_status or pretend an ingestion occurred.
The collectors retain their existing publication locks and provider budgets.
"""
import argparse
import json
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from pymongo import MongoClient

POLICIES={'tmd':('tmd:cap_warnings',timedelta(hours=1)),
          'hourly':('open_meteo:today_hourly',timedelta(hours=4))}

def decision(source,status,now=None,force=False):
    now=now or datetime.now(timezone.utc)
    if source not in POLICIES:raise ValueError('Unsupported refresh source')
    if force:return True,'explicit_request'
    if not status:return True,'no_success'
    try:
        stamp=datetime.fromisoformat(status['last_success'].replace('Z','+00:00'))
        if stamp.utcoffset()!=timedelta(0) or stamp>now+timedelta(minutes=5):raise ValueError()
    except (KeyError,TypeError,ValueError,AttributeError):return True,'invalid_success_time'
    # A new Bangkok day must have its own Today product, even after a late run.
    if source=='hourly' and status.get('forecast_date')!=(now+timedelta(hours=7)).date().isoformat():
        return True,'new_forecast_day'
    if status.get('status')=='FAILED':return True,'retry_failed_attempt'
    if now-stamp>=POLICIES[source][1]:return True,'refresh_due'
    return False,'recent_success'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',choices=list(POLICIES),required=True)
    args=parser.parse_args()
    if not os.getenv('MONGODB_URI') or not os.getenv('MONGODB_DB_NAME'):raise RuntimeError('Database configuration is required')
    try:
        with MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000) as client:
            status=client[os.environ['MONGODB_DB_NAME']].source_status.find_one({'_id':POLICIES[args.source][0]},
                {'last_success':1,'status':1,'forecast_date':1},maxTimeMS=5000)
        due,reason=decision(args.source,status,force=os.getenv('REFRESH_FORCE')=='true')
    except Exception:raise RuntimeError('Refresh due check failed; no provider request was made') from None
    print(json.dumps({'source':args.source,'due':due,'reason':reason}))
    if os.getenv('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as output:output.write('due='+str(due).lower()+'\n')

if __name__=='__main__':main()
