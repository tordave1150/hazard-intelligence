import argparse
import json
import os
from pathlib import Path
import re
from uuid import uuid4
from pymongo import MongoClient
from scripts.gistda_candidate import collect_candidate, CandidateError
from pipelines.shared.time_units import utc_now
from .data import normalize, KEY, PRODUCT
from .publication import FloodPublisher


def check_request(path=None):
    path=path or Path(__file__).resolve().parents[2]/'.github/gistda-publication-request.json'
    if path.stat().st_size>1024:raise ValueError('Request too large')
    request=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(request,dict) or set(request)!={'request_id','source_id','operation'}:
        raise ValueError('Invalid publication request')
    if request['source_id']!='gistda' or request['operation']!='publish_ongkharak_1day':
        raise ValueError('Invalid fixed publication scope')
    if not isinstance(request['request_id'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{2}',request['request_id']):
        raise ValueError('Invalid publication request ID')
    print(json.dumps({'reviewed_request_id':request['request_id'],'source_id':'gistda','scope':'1day Ongkharak only'}))


def main():
    parser = argparse.ArgumentParser(description='Publish one bounded daily Ongkharak GISTDA snapshot')
    parser.add_argument('--publish', action='store_true', required=True)
    parser.parse_args()
    if not os.getenv('MONGODB_URI'): parser.error('MONGODB_URI is required')
    status={'source_id':'gistda','product_id':PRODUCT,'etl_run_id':str(uuid4()),
            'last_attempt':utc_now(),'status':'RUNNING'}
    stage='collect'
    client=None;db=None
    try:
        client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000)
        db=client[os.getenv('MONGODB_DB_NAME','weather_db')]
        feed=normalize(collect_candidate(os.getenv('GISTDA_API_KEY','')))
        stage='publish'
        pointer=FloodPublisher(db).publish([feed],['latest'])
        status.update(status='SUCCESS',last_success=utc_now(),completed_at=utc_now(),
                      record_count=feed['record_count'],completeness=1.0,scope_area_id=feed['area_id'],
                      active_generation=pointer['active_run_id'])
        stage='save_status'
        db.source_status.update_one({'_id':KEY},{'$set':status,'$unset':{'error_summary':''}},upsert=True)
        print(json.dumps({'source_id':'gistda','status':'SUCCESS','records':feed['record_count'],
                          'area_id':feed['area_id'],'observed_at':None,'complete_provider_query':True}))
    except Exception as error:
        reason=error.reason if isinstance(error,CandidateError) else type(error).__name__
        status.update(status='FAILED',completed_at=utc_now(),error_summary=reason)
        if db is not None:
            try:db.source_status.update_one({'_id':KEY},{'$set':status},upsert=True)
            except Exception:pass
        print(json.dumps({'source_id':'gistda','status':'FAILED','stage':stage,'reason':reason}),flush=True)
        raise RuntimeError('GISTDA snapshot failed; last good district snapshot retained') from None
    finally:
        if client is not None:client.close()


if __name__=='__main__':main()
