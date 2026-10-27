import argparse,json,os
from pathlib import Path
from uuid import uuid4
from pymongo import MongoClient
from jsonschema import ValidationError
from pipelines.shared.time_units import utc_now
from .client import collect,ProviderRequestError
from .data import KEY,PRODUCT
from .publication import WarningPublisher


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');parser.add_argument('--export',type=Path)
    args=parser.parse_args()
    if not args.publish and not args.export:parser.error('Select --publish and/or --export')
    if args.publish and not os.getenv('MONGODB_URI'):parser.error('MONGODB_URI is required')
    client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000) if args.publish else None
    db=client[os.getenv('MONGODB_DB_NAME','weather_db')] if client is not None else None
    status={'source_id':'tmd','product_id':PRODUCT,'etl_run_id':str(uuid4()),'last_attempt':utc_now(),'status':'RUNNING'}
    stage='collect'
    try:
        feed=collect();stage='publish'
        if db is not None:WarningPublisher(db).publish([feed],['latest'])
        stage='save_status'
        status.update(status='SUCCESS',last_success=utc_now(),completed_at=utc_now(),record_count=len(feed['records']),
            feed_item_count=feed['feed_item_count'],ignored_item_count=feed['ignored_item_count'],completeness=1.0)
        if db is not None:db.source_status.update_one({'_id':KEY},{'$set':status,'$unset':{'error_summary':''}},upsert=True)
        if args.export:
            stage='export';args.export.parent.mkdir(parents=True,exist_ok=True);temp=args.export.with_suffix('.tmp')
            temp.write_text(json.dumps({'feed':feed,'status':status},ensure_ascii=False,allow_nan=False),encoding='utf-8');os.replace(temp,args.export)
        print(json.dumps({'source_id':'tmd','status':'SUCCESS','records':len(feed['records']),'feed_items':feed['feed_item_count']}))
    except Exception as exc:
        status.update(status='FAILED',completed_at=utc_now(),error_summary=type(exc).__name__)
        if db is not None:
            try:db.source_status.update_one({'_id':KEY},{'$set':status},upsert=True)
            except Exception:pass
        diagnostic={'source_id':'tmd','status':'FAILED','stage':stage,'error_type':type(exc).__name__}
        if isinstance(exc,ProviderRequestError):diagnostic.update(reason=exc.reason,http_status=exc.status,document_id=exc.document_id)
        if isinstance(exc,ValidationError):
            # Schema paths come from our contract, never from source values,
            # request URLs, database credentials or exception text.
            diagnostic.update(validator=exc.validator,schema_path=list(exc.absolute_schema_path))
        print(json.dumps(diagnostic),flush=True)
        raise RuntimeError('TMD feed failed; last published generation retained') from None
    finally:
        if client is not None:client.close()


if __name__=='__main__':main()
