"""Read-only audit by default; explicit rollback is bounded to validated slots."""
import argparse
import json
import os
from pymongo import MongoClient
from pipelines.shared.publication import Publisher
from pipelines.shared.schemas import validate_record
from pipelines.shared.locations import weather_locations
from pipelines.shared.quality import check_batch as check_weather
from pipelines.rid.data import DAMS, PRODUCT, check_batch as check_dams
from pipelines.rid.publication import DamPublisher
from pipelines.tmd.publication import WarningPublisher,check_envelope
from pipelines.gistda.publication import FloodPublisher,check_envelope as check_flood_envelope
from pipelines.gistda.publication import NationalFloodPublisher,check_national_envelope
from pipelines.shared.geography_migrations import canonical_stored_forecast
from pipelines.open_meteo.hourly import HourlyPublisher, check_hourly_batch
from pipelines.gistda.chunks import ThreeDayPublisher, check_chunks
from pipelines.gistda import limits as flood_limits
from pipelines.thaiwater.publication import GaugePublisher,check_envelope as check_gauge_envelope
from pipelines.thaiwater.rain_publication import RainPublisher,check_envelope as check_rain_envelope


def verify_database(db, include_retired=False):
    """Read-only active-generation, index and retention audit; no index creation."""
    specs=[('open_meteo','daily_forecast','weather_latest','location_id','Forecast',
            [a['id'] for a in weather_locations('all')],check_weather),
           ('rid',PRODUCT,'dam_latest','dam_id','DamObservation',[a['dam_id'] for a in DAMS.values()],check_dams),
           ('tmd','cap_warnings','agency_warning_latest','snapshot_id','WarningFeed',['latest'],check_envelope),
           ('gistda',flood_limits.PRODUCT,flood_limits.COLLECTION,'chunk_id','GistdaThreeDayChunk',None,check_chunks),
           ('thaiwater','national_waterlevel','gauge_latest','snapshot_id','ThaiWaterFeed',['latest'],check_gauge_envelope),
           ('thaiwater','national_rain_24h','rain_gauge_latest','snapshot_id','ThaiWaterRainFeed',['latest'],check_rain_envelope),
           ('open_meteo','today_hourly','weather_hourly_latest','location_id','HourlyForecast',[a['id'] for a in weather_locations('all')],check_hourly_batch)]
    if include_retired:
        specs += [('gistda','flood_1day_ongkharak','satellite_flood_latest','snapshot_id','GistdaFloodFeed',['latest'],check_flood_envelope),
                  ('gistda','flood_1day_thailand','satellite_flood_national_latest','snapshot_id','GistdaNationalFloodFeed',['latest'],check_national_envelope)]
    result=[]
    for source,product,collection,identity,kind,expected,check in specs:
        store=db[collection]
        total=store.count_documents({})
        document_limit=2*(flood_limits.MAX_CHUNKS if expected is None else len(expected))
        if total>document_limit:raise ValueError('Latest collection exceeds bounded retention')
        control=db.snapshot_control.find_one({'_id':f'{source}:{product}'})
        if not control:
            result.append({'source_id':source,'product_id':product,'status':'UNAVAILABLE','total_documents':total,'document_limit':document_limit})
            continue
        if expected is None:
            count=control.get('record_count')
            if type(count) is not int or not 1<=count<=flood_limits.MAX_CHUNKS:
                raise ValueError('Invalid GISTDA chunk count')
            expected=[f'{index:04d}' for index in range(count)]
            for row in store.find({}, {'slot':1,'source_id':1,'product_id':1,'etl_run_id':1}):
                if row.get('slot') not in ('A','B') or row.get('source_id')!=source or row.get('product_id')!=product:
                    raise ValueError('Unexpected document in bounded GISTDA collection')
            for slot in ('A','B'):
                if len(store.distinct('etl_run_id',{'slot':slot}))>1:
                    raise ValueError('Mixed GISTDA generations within slot')
        if control.get('active_slot') not in ['A','B'] or control.get('record_count')!=len(expected):
            raise ValueError('Invalid active snapshot pointer')
        rows=list(store.find({'source_id':source,'product_id':product,'slot':control['active_slot'],
            'etl_run_id':control['active_run_id']},{'_id':0,'slot':0,'etl_run_id':0}))
        migrated=0
        if source=='open_meteo':
            canonical=[canonical_stored_forecast(row) for row in rows]
            migrated=sum(a['location_id']!=b['location_id'] for a,b in zip(rows,canonical))
            rows=canonical
        check(rows,expected)
        for row in rows:validate_record(kind,row)
        required=[('source_id',1),('product_id',1),('slot',1),(identity,1)]
        if not any(index.get('unique') and list(index['key'].items())==required for index in store.list_indexes()):
            raise ValueError('Missing unique snapshot identity index')
        report={'source_id':source,'product_id':product,'status':'VERIFIED','active_records':len(rows),'total_documents':total,
                'document_limit':document_limit,'unique_index_verified':True}
        if migrated:report['historical_identity_aliases']=migrated
        result.append(report)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['audit','verify','rollback','unlock'])
    parser.add_argument('--source',choices=['open_meteo','hourly','rid','tmd','gistda','thaiwater','thaiwater_rain','gistda_1day','gistda_pilot'],default='open_meteo')
    parser.add_argument('--stopped-run-token',help='Exact lock token; verify the process has stopped before recovery')
    parser.add_argument('--include-retired',action='store_true',help='Explicitly audit historical stored products as well as active products')
    args=parser.parse_args()
    with MongoClient(os.environ['MONGODB_URI'],serverSelectionTimeoutMS=10000) as client:
        db=client[os.getenv('MONGODB_DB_NAME','weather_db')]
        if args.command=='audit':
            stats=[]
            for name in db.list_collection_names():
                c=db[name]
                collstats=db.command('collStats',name)
                stats.append({'collection':name,'documents':c.count_documents({}),
                              'data_bytes':collstats.get('size'),'storage_bytes':collstats.get('storageSize'),
                              'index_bytes':collstats.get('totalIndexSize'),'indexes':list(c.list_indexes())})
            print(json.dumps(stats,default=str,indent=2))
        elif args.command=='verify':
            print(json.dumps(verify_database(db,include_retired=args.include_retired),default=str,indent=2))
        elif args.command=='rollback':
            {'open_meteo':Publisher,'hourly':HourlyPublisher,'rid':DamPublisher,'tmd':WarningPublisher,'gistda':ThreeDayPublisher,'thaiwater':GaugePublisher,'thaiwater_rain':RainPublisher,'gistda_1day':NationalFloodPublisher,'gistda_pilot':FloodPublisher}[args.source](db).rollback()
            print('Previous validated slot promoted. Clear edge cache or wait up to 3 minutes.')
        else:
            if not args.stopped_run_token:parser.error('Recovery requires exact --stopped-run-token after the worker is confirmed stopped')
            key={'rid':f'rid:{PRODUCT}','tmd':'tmd:cap_warnings','open_meteo':'open_meteo:daily_forecast','hourly':'open_meteo:today_hourly','gistda':'gistda:'+flood_limits.PRODUCT,'thaiwater':'thaiwater:national_waterlevel','thaiwater_rain':'thaiwater:national_rain_24h','gistda_1day':'gistda:flood_1day_thailand','gistda_pilot':'gistda:flood_1day_ongkharak'}[args.source]
            result=db.etl_locks.delete_one({'_id':key,'token':args.stopped_run_token})
            print(json.dumps({'recovered_locks':result.deleted_count}))


if __name__=='__main__':main()
