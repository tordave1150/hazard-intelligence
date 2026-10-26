"""Fetch a single daily RID report; publish only a complete 35-dam generation."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4
from pymongo import MongoClient
from pipelines.shared.time_units import utc_now
from .client import fetch, ProviderRequestError
from .data import DAMS, PRODUCT, check_batch
from .publication import DamPublisher
from .transform import normalize


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--export',type=Path)
    args=parser.parse_args()
    if not args.publish and not args.export:
        parser.error('Select --publish and/or --export')
    if args.publish and not os.getenv('MONGODB_URI'):
        parser.error('MONGODB_URI is required')
    expected=[d['dam_id'] for d in DAMS.values()]
    status={'source_id':'rid','product_id':PRODUCT,'etl_run_id':str(uuid4()),'last_attempt':utc_now(),
        'requested_locations':len(expected),'status':'RUNNING'}
    client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000) if args.publish else None
    db=client[os.getenv('MONGODB_DB_NAME','weather_db')] if client is not None else None
    key=f'rid:{PRODUCT}'
    records=[]
    stage='fetch'
    try:
        payload,fetched=fetch()
        stage='validate'
        records=normalize(payload,fetched)
        quality=check_batch(records,expected)
        if db is not None:
            stage='publish'
            control=DamPublisher(db).publish(records,expected)
            status['active_generation']=control['active_run_id']
        stage='save_status'
        status.update(**quality,status='SUCCESS',completed_at=utc_now(),last_success=utc_now(),report_date=records[0]['report_date'])
        if db is not None:
            db.source_status.update_one({'_id':key},{'$set':status,'$unset':{'error_summary':''}},upsert=True)
        if args.export:
            stage='export'
            args.export.parent.mkdir(parents=True,exist_ok=True)
            temporary=args.export.with_suffix('.tmp')
            temporary.write_text(json.dumps({'records':records,'status':status},ensure_ascii=False,allow_nan=False),encoding='utf-8')
            os.replace(temporary,args.export)
        print(json.dumps({'source_id':'rid','status':'SUCCESS','records':len(records),'report_date':records[0]['report_date']}))
    except Exception as exc:
        status.update(status='FAILED',completed_at=utc_now(),successful_locations=len(records),
            completeness=len(records)/len(expected),error_summary=type(exc).__name__)
        if db is not None:
            db.source_status.update_one({'_id':key},{'$set':status},upsert=True)
        diagnostic={'source_id':'rid','status':'FAILED','stage':stage,'error_type':type(exc).__name__}
        if isinstance(exc,ProviderRequestError):diagnostic.update(reason=exc.reason,http_status=exc.status)
        print(json.dumps(diagnostic),flush=True)
        raise RuntimeError('RID snapshot failed; last published generation retained') from None
    finally:
        if client is not None:
            client.close()


if __name__=='__main__':main()
