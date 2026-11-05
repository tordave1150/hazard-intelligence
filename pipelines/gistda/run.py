import argparse
import json
import os
from pathlib import Path
import re
import time
import requests
from uuid import uuid4
from pymongo import MongoClient
from tempfile import TemporaryDirectory
from scripts.gistda_common import CandidateError
from pipelines.shared.time_units import utc_now
from .streaming import collect_window,WindowPublisher,WINDOWS,product
from .encoding import CURRENT_VERSION


def wait_for_receiver(get=None,sleep=None):
    get=get or requests.get;sleep=sleep or time.sleep
    for attempt in range(72):
        try:
            response=get('https://hazard-intelligence-lime.vercel.app/api/flood-products?view=summary',timeout=10)
            if response.status_code==200 and CURRENT_VERSION in response.json().get('storage_versions',[]):return
        except (requests.RequestException,ValueError):pass
        if attempt==71:raise RuntimeError('Compatible flood receiver not ready')
        sleep(5)


def check_request(path=None, *, three_day=True):
    path=path or Path(__file__).resolve().parents[2]/'.github/gistda-publication-request.json'
    if path.stat().st_size>1024:raise ValueError('Request too large')
    request=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(request,dict) or set(request)!={'request_id','source_id','operation'}:
        raise ValueError('Invalid publication request')
    if not three_day or request['source_id']!='gistda' or request['operation'] not in ['publish_thailand_3days','publish_thailand_windows','verify_thailand_windows','repack_thailand_windows','capacity_thailand_windows']:
        raise ValueError('Invalid fixed publication scope')
    if not isinstance(request['request_id'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}-\d{2}',request['request_id']):
        raise ValueError('Invalid publication request ID')
    print(json.dumps({'reviewed_request_id':request['request_id'],'source_id':'gistda','scope':'3days Thailand' if request['operation']=='publish_thailand_3days' else '3/7/30days Thailand; separate products'}))
    return request


def main():
    parser = argparse.ArgumentParser(description='Publish complete national GISTDA products using disk spooling and compressed chunks')
    parser.add_argument('--publish', action='store_true', required=True)
    scope=parser.add_mutually_exclusive_group()
    scope.add_argument('--three-day', action='store_true', help='Explicit form of the default national three-day product')
    scope.add_argument('--all-windows',action='store_true',help='Publish separate 3/7/30-day products; the map default remains 3days')
    parser.add_argument('--wait-for-receiver',action='store_true',help='Wait for the compatible production reader before writing the new storage version')
    args=parser.parse_args()
    if not os.getenv('MONGODB_URI'): parser.error('MONGODB_URI is required')
    if args.wait_for_receiver:wait_for_receiver()
    client=MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000);failed=False;budget={'remaining':300,'deadline':time.monotonic()+2700}
    try:
        db=client[os.getenv('MONGODB_DB_NAME','weather_db')];publisher=WindowPublisher(db)
        for window in WINDOWS if args.all_windows else ['3days']:
            key='gistda:'+product(window);run=str(uuid4());prior=db.source_status.find_one({'_id':key}) or {};stage='collect'
            status={'source_id':'gistda','product_id':product(window),'etl_run_id':run,'last_attempt':utc_now(),'status':'RUNNING'}
            run_id=os.getenv('GITHUB_RUN_ID','')
            if run_id.isdigit():status['run_url']='https://github.com/tordave1150/hazard-intelligence/actions/runs/'+run_id
            db.source_status.update_one({'_id':key},{'$set':status},upsert=True)
            try:
                with TemporaryDirectory(prefix='hazard-gistda-') as directory:
                    manifest=collect_window(os.getenv('GISTDA_API_KEY',''),window,directory,page_budget=budget)
                    feed=manifest['feed'];stage='publish';pointer=publisher.publish(manifest,directory)
                completed=utc_now();count=feed['record_count']
                status.update(status='SUCCESS',last_success=completed,completed_at=completed,record_count=count,provider_number_matched=count,
                              completeness=1,scope_area_id='TH',active_generation=pointer['active_generation'],storage_version=CURRENT_VERSION,
                              compressed_bytes=pointer['compressed_bytes'],archive_evicted_count=pointer['archive_evicted_count'],
                              consecutive_empty_queries=0 if count else int(prior.get('consecutive_empty_queries',0))+1)
                if count:status.update(last_nonempty_query_at=feed['fetched_at'],last_nonempty_count=count)
                db.source_status.update_one({'_id':key,'etl_run_id':run},{'$set':status,'$unset':{'error_summary':'','failure_stage':''}})
                print(json.dumps({'source_id':'gistda','status':'SUCCESS','records':count,'product_id':product(window),'product_window':window,
                                  'page_count':feed['page_count'],'stored_documents':pointer['record_count'],'compressed_bytes':pointer['compressed_bytes'],
                                  'area_id':'TH','observed_at':None,'complete_provider_query':True}),flush=True)
            except Exception as error:
                failed=True;reason=error.reason if isinstance(error,CandidateError) else type(error).__name__;completed=utc_now()
                count=getattr(error,'provider_count',None)
                if type(count) is not int or not 0<=count<=2**53-1:count=None
                status.update(status='FAILED',completed_at=completed,error_summary=reason,failure_stage=stage,last_failure_at=completed,last_failure_reason=reason,provider_number_matched=count,consecutive_empty_queries=0)
                db.source_status.update_one({'_id':key,'etl_run_id':run},{'$set':status})
                print(json.dumps({'source_id':'gistda','product_window':window,'status':'FAILED','stage':stage,'reason':reason,'provider_number_matched':count}),flush=True)
            event={k:status[k] for k in ['source_id','product_id','etl_run_id','last_attempt','completed_at','status','record_count','provider_number_matched','error_summary','failure_stage','run_url'] if k in status}
            db.gistda_flood_runs.insert_one(event)
            keep=[r['_id'] for r in db.gistda_flood_runs.find({},{'_id':1}).sort('completed_at',-1).limit(100)]
            db.gistda_flood_runs.delete_many({'_id':{'$nin':keep}})
    finally:client.close()
    if failed:raise RuntimeError('A GISTDA product failed; each last complete product remains available') from None


if __name__=='__main__':main()
