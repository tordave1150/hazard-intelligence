"""Read-only capacity and lossless compression measurements; no geometry output."""
from .streaming import WindowPublisher,WINDOWS,product,OBJECT_BUDGET_BYTES,DATABASE_CEILING_BYTES,MAX_PRODUCT_GZIP_BYTES
from .encoding import VERSIONS,CURRENT_VERSION,pack_rows


def capacity_report(db,measure=False):
    publisher=WindowPublisher(db,create_indexes=False)
    stats=db.command('dbStats',scale=1)
    sizes={r['_id']:r['compressed_bytes'] for r in publisher.objects.find({},{'compressed_bytes':1})}
    used=sum(sizes.values());logical=int(stats.get('dataSize',0))+int(stats.get('indexSize',0))
    report={'object_bytes':used,'object_limit_bytes':OBJECT_BUDGET_BYTES,'object_headroom_bytes':max(0,OBJECT_BUDGET_BYTES-used),
            'database_data_bytes':int(stats.get('dataSize',0)),'database_index_bytes':int(stats.get('indexSize',0)),
            'database_storage_bytes':int(stats.get('storageSize',0)),'database_operational_ceiling_bytes':DATABASE_CEILING_BYTES,
            'database_headroom_bytes':max(0,DATABASE_CEILING_BYTES-logical),'billing_plan_limit':'NOT_DISCOVERED',
            'measurement_encoding':CURRENT_VERSION if measure else None,'windows':[]}
    for window in WINDOWS:
        pointer=publisher.control.find_one({'_id':'gistda:'+product(window)})
        if not pointer or pointer.get('storage_version') not in VERSIONS:continue
        manifest=publisher.manifests.find_one({'_id':pointer['active_generation']})
        if not manifest:raise ValueError('Missing active flood manifest')
        count=manifest['compressed_bytes']
        entry={'window':window,'generation':manifest['_id'],'storage_version':manifest['storage_version'],
               'record_count':manifest['feed']['record_count'],'fetched_at':manifest['feed']['fetched_at'],
               'compressed_bytes':count,'product_limit_bytes':MAX_PRODUCT_GZIP_BYTES,
               'product_headroom_bytes':max(0,MAX_PRODUCT_GZIP_BYTES-count),
               'unchanged_same_encoding_query_added_bytes':0,'requires_storage_migration':manifest['storage_version']!=CURRENT_VERSION,
               'fully_changed_next_query_object_bytes':used+count,
               'fully_changed_next_query_fits_object_budget':used+count<=OBJECT_BUDGET_BYTES}
        if measure:
            measured=0;objects={c['hash']:c for c in manifest['chunks']}
            for row in publisher.objects.find({'_id':{'$in':list(objects)}}).batch_size(20):
                from .streaming import checked_payload
                rows=checked_payload(objects[row['_id']],bytes(row['payload']),manifest['storage_version'])
                raw,packed=pack_rows(rows)
                from .encoding import unpacked
                if unpacked(raw,CURRENT_VERSION)!=rows:raise ValueError('Lossless encoding round trip failed')
                measured+=len(packed);objects.pop(row['_id'])
            if objects:raise ValueError('Missing flood objects during capacity measurement')
            entry.update(measured_compressed_bytes=measured,measured_saved_bytes=count-measured)
        report['windows'].append(entry)
    return report
