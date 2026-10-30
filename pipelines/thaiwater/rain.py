import argparse
import json
import os
from pathlib import Path
from pymongo import MongoClient
from pipelines.shared.run_status import start_run
from pipelines.shared.time_units import utc_now
from .client import fetch,ProviderRequestError
from .rain_data import KEY,PRODUCT,normalize,SOURCE
from .rain_publication import RainPublisher


def main():
    parser=argparse.ArgumentParser(description='Publish the complete unfiltered Thailand rain station response')
    parser.add_argument('--publish',action='store_true');parser.add_argument('--export',type=Path)
    args=parser.parse_args()
    if not args.publish and not args.export:parser.error('Select --publish and/or --export')
    if args.publish and not os.getenv('MONGODB_URI'):parser.error('MONGODB_URI is required')
    client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000) if args.publish else None
    db=client[os.getenv('MONGODB_DB_NAME','weather_db')] if client is not None else None
    status={'source_id':'thaiwater','product_id':PRODUCT,'last_attempt':utc_now()};stage='collect'
    try:
        start_run(db,KEY,status)
        payload,fetched=fetch(source=SOURCE);stage='validate';feed=normalize(payload,fetched)
        if db is not None:
            stage='publish';control=RainPublisher(db).publish([feed],['latest']);status['active_generation']=control['active_run_id']
        stage='save_status'
        status.update(status='SUCCESS',last_success=utc_now(),completed_at=utc_now(),record_count=feed['record_count'],
            provider_automatic_count=feed['provider_automatic_count'],excluded_station_count=len(feed['excluded_stations']),
            province_count=len(feed['coverage_by_province']),
            quality_issue_count=feed['quality_issue_count'],time_unknown_count=feed['time_unknown_count'],scope_area_id='TH',completeness=1.0)
        if db is not None:db.source_status.update_one({'_id':KEY},{'$set':status,'$unset':{'error_summary':'','error_stage':''}},upsert=True)
        if args.export:
            args.export.parent.mkdir(parents=True,exist_ok=True);temp=args.export.with_suffix('.tmp')
            temp.write_text(json.dumps({'feed':feed,'status':status},ensure_ascii=False,allow_nan=False),encoding='utf-8');os.replace(temp,args.export)
        print(json.dumps({k:status[k] for k in ('source_id','status','record_count','provider_automatic_count','excluded_station_count','province_count','quality_issue_count','time_unknown_count','scope_area_id')}))
    except Exception as error:
        reason=error.reason if isinstance(error,ProviderRequestError) else type(error).__name__
        status.update(status='FAILED',completed_at=utc_now(),error_summary=reason,error_stage=stage)
        if db is not None:
            try:db.source_status.update_one({'_id':KEY},{'$set':status},upsert=True)
            except Exception:pass
        print(json.dumps({'source_id':'thaiwater','status':'FAILED','reason':reason,'stage':stage}),flush=True)
        raise RuntimeError('Station refresh failed; last complete response retained') from None
    finally:
        if client is not None:client.close()


if __name__=='__main__':main()
