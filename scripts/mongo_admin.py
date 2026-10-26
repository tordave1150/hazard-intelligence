"""Read-only audit by default; explicit rollback is bounded to validated slots."""
import argparse
import json
import os
from pymongo import MongoClient
from pipelines.shared.publication import Publisher


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['audit','rollback','unlock'])
    parser.add_argument('--stopped-run-token',help='Exact lock token; verify the process has stopped before recovery')
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
        elif args.command=='rollback':
            Publisher(db).rollback()
            print('Previous validated slot promoted. Clear edge cache or wait up to 3 minutes.')
        else:
            if not args.stopped_run_token:parser.error('Recovery requires exact --stopped-run-token after the worker is confirmed stopped')
            result=db.etl_locks.delete_one({'_id':'open_meteo:daily_forecast','token':args.stopped_run_token})
            print(json.dumps({'recovered_locks':result.deleted_count}))


if __name__=='__main__':main()
