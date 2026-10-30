"""Real-engine qualification on an owned loopback MongoDB and disposable data.

Never reads Atlas credentials or accepts a remote URI. Starts/stops only its own
processes. Public captures are loaded from ignored local preview files.
"""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import requests
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure,PyMongoError
from pipelines.shared.publication import Publisher
from pipelines.rid.publication import DamPublisher
from pipelines.tmd.publication import WarningPublisher
from pipelines.gistda.publication import NationalFloodPublisher
from scripts.mongo_admin import verify_database

ROOT=Path(__file__).resolve().parents[1]
PORT=27028
WEB_PORT=3002


def stop(process):
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=15)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)


def free_port(port):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',port))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mongod',type=Path,required=True)
    args=parser.parse_args();executable=args.mongod.resolve()
    if not executable.is_file():parser.error('Provide an official, checksum-verified mongod executable')
    free_port(PORT);free_port(WEB_PORT)
    run_id=uuid4().hex[:12];folder=(ROOT/'artifacts'/f'mongo-qualification-{run_id}').resolve()
    if not folder.is_relative_to(ROOT/'artifacts'):raise ValueError('Test data path escaped workspace')
    folder.mkdir();data=folder/'db';data.mkdir()
    database='hazard_qualification_'+run_id
    environment=os.environ.copy();environment.pop('MONGODB_URL',None)
    environment.update(MONGODB_URI=f'mongodb://127.0.0.1:{PORT}',MONGODB_DB_NAME=database,
        HAZARD_LOCAL_SNAPSHOT='1',NODE_ENV='production',PYTHONIOENCODING='utf-8')
    events=[];mongo=None;web=None
    mongo_log=(folder/'mongo.log').open('ab');web_log=(folder/'web.log').open('ab')
    creation=getattr(subprocess,'CREATE_NO_WINDOW',0)
    client=MongoClient(environment['MONGODB_URI'],serverSelectionTimeoutMS=500,connectTimeoutMS=500)
    def record(name,**details):
        event={'check':name,'status':'PASS',**details};events.append(event);print(json.dumps(event),flush=True)
    def start_mongo():
        process=subprocess.Popen([str(executable),'--bind_ip','127.0.0.1','--port',str(PORT),'--dbpath',str(data)],
            stdout=mongo_log,stderr=subprocess.STDOUT,creationflags=creation)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Local test MongoDB exited; inspect its local log')
            try:client.admin.command('ping');return process
            except PyMongoError:time.sleep(.25)
        stop(process);raise RuntimeError('Local test MongoDB did not become ready')
    def start_web():
        process=subprocess.Popen([shutil.which('node'),str(ROOT/'node_modules/next/dist/bin/next'),'start',
            '--hostname','127.0.0.1','--port',str(WEB_PORT)],cwd=ROOT/'apps/web',env=environment,
            stdout=web_log,stderr=subprocess.STDOUT,creationflags=creation)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Local test web server exited; inspect its local log')
            try:
                if requests.get(f'http://127.0.0.1:{WEB_PORT}/',timeout=2).status_code==200:return process
            except requests.RequestException:pass
            time.sleep(.25)
        stop(process);raise RuntimeError('Local test web server did not become ready')
    def read(route):
        response=requests.get(f'http://127.0.0.1:{WEB_PORT}'+route,timeout=20)
        assert response.status_code==200
        assert environment['MONGODB_URI'] not in response.text
        return response.json()
    def cli(*args):
        subprocess.run([sys.executable,'-m','scripts.mongo_admin',*args],cwd=ROOT,env=environment,
            check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=creation)
    try:
        mongo=start_mongo();db=client[database]
        weather=json.loads((ROOT/'apps/web/data/local/weather.json').read_text(encoding='utf-8'))['records']
        dams=json.loads((ROOT/'apps/web/data/local/dams.json').read_text(encoding='utf-8'))['records']
        feed=json.loads((ROOT/'apps/web/data/local/warnings.json').read_text(encoding='utf-8'))['feed']
        flood=json.loads((ROOT/'tests/fixtures/gistda/synthetic-national-feed.json').read_text(encoding='utf-8'))
        assert len(weather)==1005 and len(dams)==35 and feed['records']
        specs=[(Publisher(db),weather,[r['location_id'] for r in weather]),
               (DamPublisher(db),dams,[r['dam_id'] for r in dams]),(WarningPublisher(db),[feed],['latest']),
               (NationalFloodPublisher(db),[flood],['latest'])]
        for publisher,rows,ids in specs:publisher.publish(rows,ids)
        original={row['_id']:row['active_run_id'] for row in db.snapshot_control.find()}
        newer=deepcopy(weather);newer[0]['ingested_at']=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        changed_dams=deepcopy(dams);changed_dams[0]['ingested_at']=newer[0]['ingested_at']
        empty=deepcopy(feed);empty.update(records=[],feed_item_count=0,ignored_item_count=0)
        specs[0][0].publish(newer,specs[0][2]);specs[1][0].publish(changed_dams,specs[1][2]);specs[2][0].publish([empty],['latest'])
        empty_flood=deepcopy(flood);empty_flood.update(records=[],record_count=0)
        specs[3][0].publish([empty_flood],['latest'])
        web=start_web()
        assert read('/api/overview')['records'][0]['ingested_at']==newer[0]['ingested_at']
        assert len(read('/api/dams')['records'])==35
        empty_response=read('/api/warnings');assert empty_response['feed'] and empty_response['records']==[]
        empty_flood_response=read('/api/flood-products')
        assert empty_flood_response['feed'] and empty_flood_response['records']==[] and empty_flood_response['status']=='EMPTY_RESULT'
        record('real_engine_publication_and_empty_feed',engine=client.server_info()['version'],weather=1005,dams=35,cap_messages=0)
        for source in ['open_meteo','rid','tmd','gistda']:cli('rollback','--source',source)
        stop(web);web=start_web()
        assert read('/api/overview')['records']==weather and read('/api/dams')['records']==dams
        assert read('/api/warnings')['records']==feed['records']
        assert read('/api/flood-products')['records']==flood['records']
        assert all(row['active_run_id']==original[row['_id']] for row in db.snapshot_control.find())
        record('cli_rollback_restores_all_four_original_generations',cap_messages=len(feed['records']),gistda_features=len(flood['records']))
        publisher,_,ids=specs[0];before=db.snapshot_control.find_one({'_id':'open_meteo:daily_forecast'})
        insert=publisher.records.insert_many
        def partial(rows,**kwargs):
            insert(rows[:10]);raise ConnectionFailure('Deliberate disposable test interruption')
        with patch.object(publisher.records,'insert_many',side_effect=partial):
            try:publisher.publish(newer,ids);raise AssertionError('Interrupted candidate was promoted')
            except ConnectionFailure:pass
        assert db.snapshot_control.find_one({'_id':before['_id']})==before and publisher.read()==weather
        try:publisher.rollback();raise AssertionError('Reused previous generation was accepted')
        except ValueError:pass
        record('partial_candidate_retains_active_and_reused_rollback_is_rejected')
        code="import os;from pymongo import MongoClient;from pipelines.shared.publication import Publisher;db=MongoClient(os.environ['MONGODB_URI'])[os.environ['MONGODB_DB_NAME']];lock=Publisher(db).lock('open_meteo:daily_forecast');lock.__enter__();os._exit(23)"
        child=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=environment,creationflags=creation)
        assert child.returncode==23
        lock=db.etl_locks.find_one({'_id':'open_meteo:daily_forecast'});assert lock
        try:publisher.publish(newer,ids);raise AssertionError('Orphan lock was ignored')
        except RuntimeError:pass
        assert publisher.read()==weather
        cli('unlock','--source','open_meteo','--stopped-run-token',lock['token'])
        assert db.etl_locks.count_documents({})==0
        record('hard_exit_lock_blocks_writer_and_exact_token_recovers_after_exit')
        stop(mongo);mongo=None;stop(web);web=start_web()
        for route in ['/api/overview','/api/dams','/api/warnings','/api/flood-products']:
            value=read(route);assert value['records']==[] and value['freshness']=='UNAVAILABLE' and value['storage']=='mongo' and value['error']
        record('real_database_outage_returns_unavailable_without_local_fallback')
        mongo=start_mongo();stop(web);web=start_web()
        assert read('/api/overview')['records']==weather and read('/api/dams')['records']==dams
        assert read('/api/warnings')['records']==feed['records']
        assert read('/api/flood-products')['records']==flood['records']
        report=verify_database(db,include_retired=True)
        tested={(rows[0]['source_id'],rows[0]['product_id']) for _,rows,_ in specs}
        assert all(r['status']=='VERIFIED' for r in report if (r['source_id'],r['product_id']) in tested)
        assert next(r for r in report if r['product_id']=='flood_1day_ongkharak')['status']=='UNAVAILABLE'
        record('database_restart_recovers_previous_data_and_indexes',verification=report)
        outcome={'status':'PASS','time':datetime.now(timezone.utc).isoformat(),'database':database,'events':events,
                 'scope':'Disposable local MongoDB and production-mode Next.js; no Atlas operation or provider request.'}
        (ROOT/'artifacts/mongo-qualification-report.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
        print('Qualification report saved to artifacts/mongo-qualification-report.json',flush=True)
    finally:
        stop(web);client.close();stop(mongo);mongo_log.close();web_log.close()


if __name__=='__main__':main()
