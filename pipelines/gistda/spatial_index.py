"""Build derived spatial indexes for retained queries without provider requests."""
from copy import deepcopy
from bson import BSON,Binary
from .streaming import WindowPublisher,checked_payload,validate_manifest,OBJECT_BUDGET_BYTES,DATABASE_CEILING_BYTES
from .spatial import build_spatial,checked_spatial,SPATIAL_BUDGET_BYTES
from pipelines.shared.time_units import utc_now
from scripts.gistda_common import CandidateError


def index_query(db,generation,check_database=True):
    publisher=WindowPublisher(db,create_indexes=False)
    original=publisher.manifests.find_one({'_id':generation,'state':'PUBLISHED','geometry_available':True})
    if not original:raise ValueError('Retained geometry unavailable for indexing')
    validate_manifest(original)
    if original.get('spatial_index_version')==1:return {'generation':generation,'status':'ALREADY_INDEXED'}
    descriptors={c['hash']:c for c in original['chunks']};derived={}
    for row in publisher.objects.find({'_id':{'$in':list(descriptors)}}).batch_size(20):
        c=descriptors[row['_id']];rows=checked_payload(c,bytes(row['payload']),original['storage_version'])
        fields,packed=build_spatial(rows);checked_spatial({**c,**fields},packed,rows)
        derived[row['_id']]=(fields,packed)
    if len(derived)!=len(descriptors):raise ValueError('Missing source objects for index')
    candidate=deepcopy(original);candidate.update(spatial_index_version=1,spatial_indexed_at=utc_now())
    candidate['chunks']=[{**c,**derived[c['hash']][0]} for c in original['chunks']]
    validate_manifest(candidate)
    if len(BSON.encode(candidate))>1024*1024:raise CandidateError('MANIFEST_SIZE_EXCEEDED')
    with publisher.lock():
        current=publisher.manifests.find_one({'_id':generation,'state':'PUBLISHED','geometry_available':True})
        if not current or current['feed']!=original['feed'] or current['chunks']!=original['chunks']:raise ValueError('Query changed while indexing')
        existing={r['_id']:r for r in publisher.spatial.find({},{'payload':0})}
        added={key:value for key,value in derived.items() if key not in existing}
        old_bytes=sum(r['compressed_bytes'] for r in existing.values());new_bytes=sum(len(v[1]) for v in added.values())
        if old_bytes+new_bytes>SPATIAL_BUDGET_BYTES:raise CandidateError('SPATIAL_STORAGE_BUDGET_EXCEEDED')
        geometry_bytes=sum(r['compressed_bytes'] for r in publisher.objects.find({},{'compressed_bytes':1}))
        if geometry_bytes+old_bytes+new_bytes>OBJECT_BUDGET_BYTES:raise CandidateError('COMPRESSED_STORAGE_BUDGET_EXCEEDED')
        if check_database:
            stats=db.command('dbStats',scale=1)
            if stats.get('dataSize',0)+stats.get('indexSize',0)+new_bytes+len(added)*1024+len(BSON.encode(candidate))>DATABASE_CEILING_BYTES:raise CandidateError('DATABASE_STORAGE_BUDGET_EXCEEDED')
        for key,(fields,_) in derived.items():
            if key in existing and any(existing[key].get(k)!=fields[v] for k,v in [('hash','spatial_hash'),('raw_bytes','spatial_raw_bytes'),('compressed_bytes','spatial_compressed_bytes')]):raise ValueError('Existing index identity mismatch')
        try:
            pending=[]
            for key,(fields,packed) in added.items():
                pending.append({'_id':key,'payload':Binary(packed),'hash':fields['spatial_hash'],'raw_bytes':fields['spatial_raw_bytes'],'compressed_bytes':len(packed)})
                if len(pending)==100:publisher.spatial.insert_many(pending,ordered=True);pending=[]
            if pending:publisher.spatial.insert_many(pending,ordered=True)
            result=publisher.manifests.update_one({'_id':generation,'geometry_available':True},{'$set':{k:candidate[k] for k in ['spatial_index_version','spatial_indexed_at','chunks']}})
            if result.matched_count!=1:raise ValueError('Query disappeared before index promotion')
        except Exception:
            publisher._gc();raise
    return {'generation':generation,'window':original['product_window'],'status':'INDEXED','record_count':original['feed']['record_count'],
            'fetched_at':original['feed']['fetched_at'],'spatial_compressed_bytes':sum(len(v[1]) for v in derived.values())}
