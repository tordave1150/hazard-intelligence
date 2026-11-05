"""Disk-spooled, complete national products; immutable compressed chunks in MongoDB.

Only geometry and canonical administrative membership survive normalization.
Query history is distinct from acquisition history; no observation time is invented.
"""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import gzip
import msgpack
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from copy import deepcopy
from uuid import uuid4
from bson import Binary,BSON
import requests
from pymongo.errors import DuplicateKeyError
from jsonschema import Draft202012Validator,FormatChecker
from pipelines.shared.locations import load_areas
from pipelines.shared.time_units import utc_now,instant
from scripts.gistda_common import CandidateError,_strict_object
from scripts.gistda_sample_quality import administrative_quality,geometry_quality
from scripts.probe_gistda_features import page_metadata
from .encoding import VERSIONS,CURRENT_VERSION,checked_raw,unpacked,binary_rows,pack_rows

WINDOWS=('3days','7days','30days')
PAGE_SIZE=1000
MAX_FEATURES=250_000
MAX_PAGES=250
MAX_SOURCE_BYTES=768*1024*1024
MAX_NORMALIZED_BYTES=512*1024*1024
MAX_POSITIONS=12_000_000
MAX_SECONDS=1200
CHUNK_ROWS=100
CHUNK_RAW_BYTES=1024*1024
MAX_CHUNKS=5000
MAX_PRODUCT_GZIP_BYTES=128*1024*1024
OBJECT_BUDGET_BYTES=320*1024*1024
DATABASE_CEILING_BYTES=400*1024*1024
HISTORY_DAYS=30
REPACK_GRACE_SECONDS=120  # Reader manifest cache is 30s; preserve in-flight old pages.
LOCK='gistda:flood_windows'
AREAS={a['id']:a for a in load_areas()}
SCHEMA=json.loads((Path(__file__).resolve().parents[2]/'packages/contracts/flood-window.schema.json').read_text(encoding='utf-8'))
VALIDATE=Draft202012Validator(SCHEMA,format_checker=FormatChecker())


def encoded(value):return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
def product(window):
    if window not in WINDOWS:raise ValueError('Unsupported flood window')
    return 'flood_'+window+'_thailand'


def validate_manifest(manifest):
    feed=manifest['feed'];VALIDATE.validate(feed);window=manifest['product_window']
    if manifest.get('storage_version') not in VERSIONS or window not in WINDOWS or feed['product_window']!=window or feed['product_id']!=product(window) or feed['source_url']!='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/'+window:raise ValueError('Invalid flood provenance')
    if instant(feed['response_at'])>instant(feed['fetched_at'])+timedelta(minutes=5) or instant(feed['fetched_at'])>instant(feed['ingested_at']):raise ValueError('Invalid flood clocks')
    if len(manifest['chunks'])>MAX_CHUNKS:raise ValueError('Flood chunk budget exceeded')
    index={};total=0;hashes=set()
    for i,c in enumerate(manifest['chunks']):
        if c['hash'] in hashes or len(c['hash'])!=64 or any(ch not in '0123456789abcdef' for ch in c['hash']) or not 1<=c['count']<=CHUNK_ROWS or not 1<=c['compressed_bytes']<=CHUNK_RAW_BYTES or not 1<=c['raw_bytes']<=CHUNK_RAW_BYTES:raise ValueError('Invalid flood descriptor')
        hashes.add(c['hash']);total+=c['count'];district=AREAS.get(c['area_ids'][-1])
        if not district or district['level']!='district':raise ValueError('Invalid flood district')
        province=district['province_id']
        if c['area_ids']!=['TH',AREAS[province]['region_id'],province,district['id']]:raise ValueError('Invalid flood hierarchy')
        for area_id in c['area_ids']:
            entry=index.setdefault(area_id,{'count':0,'chunks':[]});entry['count']+=c['count'];entry['chunks'].append(i)
    if total!=feed['record_count'] or index!=manifest['areas'] or sum(c['compressed_bytes'] for c in manifest['chunks'])!=manifest['compressed_bytes']:raise ValueError('Incomplete flood accounting')


def normalized_feature(feature,secret):
    props=feature['properties'];admin=administrative_quality(props)
    if admin['province_district_relationship']!='MATCH':raise CandidateError('ADMINISTRATIVE_IDENTITY_MISMATCH')
    quality=geometry_quality(feature.get('geometry'),'crs' in feature)
    if quality['status']!='SYNTAX_AND_TOPOLOGY_VALID' or not quality['within_pinned_thailand_bbox']:raise CandidateError('INVALID_OR_UNVERIFIED_GEOMETRY')
    geometry={key:feature['geometry'][key] for key in ('type','coordinates')}
    province='TH-P-'+str(props['pv_idn']);district='TH-D-'+str(props['ap_idn'])
    supplied=next((v for v in [feature.get('id'),props.get('_id'),props.get('mongo_id')] if v is not None and v!=''),None)
    if supplied is not None:
        if type(supplied) not in (str,int) or len(str(supplied))>256 or secret in str(supplied):raise CandidateError('INVALID_PROVIDER_IDENTITY')
        identity=hashlib.sha256(encoded(['provider',str(supplied)])).hexdigest()
    else:identity=hashlib.sha256(encoded(['geometry',geometry,province,district])).hexdigest()
    row={'type':'Feature','id':hashlib.sha256(encoded([identity,geometry,province,district])).hexdigest(),
         'geometry':geometry,'properties':None,'area_ids':[province,district]}
    return identity,row,quality['positions_checked']


def collect_window(api_key,window,directory,get=None,clock=time.monotonic,now=None,page_budget=None,storage_version=CURRENT_VERSION):
    """At most one bounded source page and one output chunk reside in memory."""
    if window not in WINDOWS:raise CandidateError('INVALID_PRODUCT_WINDOW')
    if storage_version not in VERSIONS:raise ValueError('Unsupported flood storage encoding')
    api_key=api_key.strip()
    if not 8<=len(api_key)<=4096 or any(c in api_key for c in '\r\n') or api_key.lower().startswith(('http:','https:','gistda_api_key=')):raise CandidateError('INVALID_OR_MISSING_SECRET')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    database=sqlite3.connect(directory/'spool.sqlite')
    database.execute('CREATE TABLE features (identity TEXT PRIMARY KEY, id TEXT UNIQUE, district TEXT, data BLOB)')
    endpoint='https://api-gateway.gistda.or.th/api/2.0/resources/features/flood/'+window
    matched=None;count=source_bytes=raw_bytes=positions=0;stamps=[];deadline=clock()+MAX_SECONDS
    if page_budget and 'deadline' in page_budget:deadline=min(deadline,page_budget['deadline'])
    fetched_at=None
    try:
        for page in range(MAX_PAGES):
            if clock()>deadline:raise CandidateError('DEADLINE_EXCEEDED')
            if page_budget is not None:
                if page_budget['remaining']<=0:raise CandidateError('SOURCE_REQUEST_BUDGET_EXCEEDED')
                page_budget['remaining']-=1
            with (get or requests.get)(endpoint,params={'limit':PAGE_SIZE,'offset':count},headers={'Accept':'application/json','API-Key':api_key},timeout=(5,25),allow_redirects=False,stream=True) as response:
                if response.status_code in (401,403):raise CandidateError('AUTHENTICATION_OR_ENTITLEMENT_ERROR')
                if response.status_code!=200:raise CandidateError('HTTP_ERROR_NOT_AN_EMPTY_COLLECTION')
                parts=[];page_bytes=0
                for block in response.iter_content(65536):
                    source_bytes+=len(block);page_bytes+=len(block)
                    if page_bytes>8*1024*1024 or source_bytes>MAX_SOURCE_BYTES:raise CandidateError('RESPONSE_TOO_LARGE')
                    if clock()>deadline:raise CandidateError('DEADLINE_EXCEEDED')
                    parts.append(block)
                try:
                    def reject_constant(_):raise ValueError('Non-finite JSON')
                    payload=json.loads(b''.join(parts).decode('utf-8-sig'),object_pairs_hook=_strict_object,parse_constant=reject_constant)
                except (ValueError,UnicodeError,RecursionError):raise CandidateError('INVALID_JSON') from None
            fetched_at=now() if now else utc_now()
            if isinstance(payload,dict) and (payload.get('error') or any(type(payload.get(k)) is int and payload[k]>=400 for k in ['status','statusCode','status_code'])):raise CandidateError('PROVIDER_ERROR_NOT_AN_OBSERVATION')
            try:
                meta=page_metadata(payload,limit=PAGE_SIZE)
                stamp=datetime.fromisoformat(meta['response_timestamp'].replace('Z','+00:00'))
                fetched=datetime.fromisoformat(fetched_at.replace('Z','+00:00'))
                if fetched.utcoffset()!=timedelta(0) or stamp>fetched+timedelta(minutes=5):raise ValueError()
            except (ValueError,TypeError,KeyError):raise CandidateError('INVALID_COLLECTION_METADATA') from None
            if 'crs' in payload:raise CandidateError('UNVERIFIED_COORDINATE_REFERENCE')
            if matched is None:matched=meta['number_matched']
            if meta['number_matched']!=matched:raise CandidateError('PROVIDER_COUNT_CHANGED_DURING_PAGINATION')
            if matched>MAX_FEATURES:raise CandidateError('NATIONAL_FEATURE_BUDGET_EXCEEDED')
            stamps.append(meta['response_timestamp'])
            for feature in payload['features']:
                identity,row,n=normalized_feature(feature,api_key);data=encoded(row)
                raw_bytes+=len(data);positions+=n
                if raw_bytes>MAX_NORMALIZED_BYTES or positions>MAX_POSITIONS:raise CandidateError('CANDIDATE_GEOMETRY_LIMIT')
                try:database.execute('INSERT INTO features VALUES (?,?,?,?)',(identity,row['id'],row['area_ids'][1],data))
                except sqlite3.IntegrityError:raise CandidateError('DUPLICATE_OR_REPEATED_PROVIDER_FEATURE') from None
                count+=1
            database.commit()
            if count>matched:raise CandidateError('INVALID_COLLECTION_METADATA')
            if count==matched:break
            if not payload['features']:raise CandidateError('INCOMPLETE_QUERY_NOT_PUBLISHABLE')
        else:raise CandidateError('INCOMPLETE_QUERY_NOT_PUBLISHABLE')
        chunks=[];index={};batch=[];batch_bytes=2;district=None;compressed_bytes=0
        def flush():
            nonlocal batch,batch_bytes,compressed_bytes
            if not batch:return
            raw=b'['+b','.join(batch)+b']' if storage_version=='gzip-v1' else msgpack.Packer().pack_array_header(len(batch))+b''.join(batch)
            digest=hashlib.sha256(raw).hexdigest();packed=gzip.compress(raw,mtime=0)
            if len(raw)>CHUNK_RAW_BYTES:raise CandidateError('CHUNK_BYTE_BUDGET_EXCEEDED')
            compressed_bytes+=len(packed)
            if compressed_bytes>MAX_PRODUCT_GZIP_BYTES or len(chunks)>=MAX_CHUNKS:raise CandidateError('COMPRESSED_STORAGE_BUDGET_EXCEEDED')
            (directory/(digest+'.gz')).write_bytes(packed)
            member=AREAS[district];province=member['province_id'];region=AREAS[province]['region_id']
            descriptor={'hash':digest,'count':len(batch),'raw_bytes':len(raw),'compressed_bytes':len(packed),'area_ids':['TH',region,province,district]}
            for area_id in descriptor['area_ids']:
                entry=index.setdefault(area_id,{'count':0,'chunks':[]});entry['count']+=len(batch);entry['chunks'].append(len(chunks))
            chunks.append(descriptor);batch=[];batch_bytes=2
        for current,data in database.execute('SELECT district,data FROM features ORDER BY district,id'):
            if storage_version==CURRENT_VERSION:data=binary_rows(json.loads(data))
            if district!=current or batch and (len(batch)>=CHUNK_ROWS or batch_bytes+len(data)+1>CHUNK_RAW_BYTES):flush()
            if len(data)+2>CHUNK_RAW_BYTES:raise CandidateError('INDIVIDUAL_FEATURE_TOO_LARGE')
            district=current;batch.append(data);batch_bytes+=len(data)+1
        flush()
        feed={'schema_version':'3.0','source_id':'gistda','product_id':product(window),'product_window':window,'data_state':'satellite_observation','snapshot_id':'latest',
              'area_id':'TH','query':{'limit':PAGE_SIZE,'offset':0},'page_count':len(stamps),'pagination_consistency':'COUNT_AND_DUPLICATES_CHECKED_NO_VERSION_TOKEN',
              'source_url':endpoint,'attribution':'GISTDA Disaster Platform','response_at':min(stamps,key=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))),
              'fetched_at':fetched_at,'ingested_at':now() if now else utc_now(),'observed_at':None,'observation_time_status':'NOT_SUPPLIED','complete_provider_query':True,'record_count':count,
              'coverage':f'Unfiltered provider {window} query; valid satellite coverage and clear observations unknown',
              'area_metrics':'NOT_USED_UNITS_UNVERIFIED','interpretation':'Retrospective footprints; current flood state unknown. Empty is not an all-clear.'}
        manifest={'_id':str(uuid4()),'storage_version':storage_version,'source_id':'gistda','product_window':window,'feed':feed,'chunks':chunks,'areas':index,
                  'geometry_available':True,'compressed_bytes':compressed_bytes,'source_bytes':source_bytes,'normalized_bytes':raw_bytes,'positions':positions}
        if len(BSON.encode(manifest))>1024*1024:raise CandidateError('MANIFEST_SIZE_EXCEEDED')
        validate_manifest(manifest);return manifest
    except CandidateError as error:
        error.provider_count=matched
        raise
    except requests.RequestException:raise CandidateError('TRANSPORT_FAILURE') from None
    finally:database.close()


def checked_payload(descriptor,data,version='gzip-v1'):
    rows=unpacked(checked_raw(descriptor,data),version)
    if len(rows)!=descriptor['count']:raise ValueError('Invalid chunk accounting')
    return rows


class WindowPublisher:
    def __init__(self,db,create_indexes=True):
        self.db=db;self.objects=db.gistda_flood_objects;self.manifests=db.gistda_flood_manifests;self.control=db.snapshot_control
        if create_indexes:self.manifests.create_index([('product_window',1),('state',1),('feed.fetched_at',-1)])

    @contextmanager
    def lock(self):
        token=str(uuid4())
        try:self.db.etl_locks.insert_one({'_id':LOCK,'token':token,'started_at':utc_now()})
        except DuplicateKeyError:raise RuntimeError('Another flood writer or unrecovered run holds the lock') from None
        try:yield
        finally:self.db.etl_locks.delete_one({'_id':LOCK,'token':token})

    def _retained(self):
        pointers=list(self.control.find({'_id':{'$in':['gistda:'+product(w) for w in WINDOWS]}}))
        protected=set()
        for pointer in pointers:
            if pointer.get('storage_version') in VERSIONS:protected.add(pointer['active_generation'])
            previous=pointer.get('previous') or {}
            if previous.get('storage_version') in VERSIONS:protected.add(previous['active_generation'])
        protected.update(r['_id'] for r in self.manifests.find({'retire_after':{'$gt':utc_now()}},{'_id':1}))
        return protected

    def _gc(self,extra=None):
        protected=self._retained();cutoff=(datetime.now(timezone.utc)-timedelta(days=HISTORY_DAYS)).isoformat()
        now=utc_now()
        for row in self.manifests.find({}, {'_id':1,'state':1,'feed.fetched_at':1,'product_window':1,'retire_after':1,'replaced_by':1}):
            if row.get('retire_after','')>now:continue
            if row['_id'] not in protected and (row.get('replaced_by') or row.get('state')!='PUBLISHED' or row.get('product_window')!='3days' or row['feed']['fetched_at']<cutoff):self.manifests.delete_one({'_id':row['_id']})
        # One archived query snapshot per UTC day; active/previous remain protected.
        days=set()
        for row in self.manifests.find({'state':'PUBLISHED','product_window':'3days'}).sort('feed.fetched_at',-1):
            if row.get('retire_after','')>now:continue
            day=row['feed']['fetched_at'][:10]
            if day in days and row['_id'] not in protected:self.manifests.delete_one({'_id':row['_id']})
            else:days.add(day)
        references=set(extra or [])
        for row in self.manifests.find({'geometry_available':True},{'chunks.hash':1}):references.update(c['hash'] for c in row['chunks'])
        self.objects.delete_many({'_id':{'$nin':list(references)}})

    def publish(self,manifest,directory,check_database=True,replaces_generation=None):
        directory=Path(directory);window=manifest['product_window'];key='gistda:'+product(window)
        validate_manifest(manifest)
        if manifest['compressed_bytes']>MAX_PRODUCT_GZIP_BYTES:raise CandidateError('COMPRESSED_STORAGE_BUDGET_EXCEEDED')
        for descriptor in manifest['chunks']:checked_payload(descriptor,(directory/(descriptor['hash']+'.gz')).read_bytes(),manifest['storage_version'])
        with self.lock():
            self._gc();active=self.control.find_one({'_id':key})
            old=self.manifests.find_one({'_id':active.get('active_generation')}) if active and active.get('storage_version') in VERSIONS else None
            if replaces_generation and (not old or old['_id']!=replaces_generation or old['feed']!=manifest['feed'] or old['areas']!=manifest['areas']):raise ValueError('Repack source generation changed')
            if old and instant(manifest['feed']['fetched_at'])<instant(old['feed']['fetched_at']):raise ValueError('Older flood query cannot replace active generation')
            known={row['_id']:row['compressed_bytes'] for row in self.objects.find({}, {'compressed_bytes':1})}
            added={c['hash']:c['compressed_bytes'] for c in manifest['chunks'] if c['hash'] not in known}
            projected=sum(known.values())+sum(added.values())
            evicted=0;protected=self._retained()
            for archive in self.manifests.find({'state':'PUBLISHED','geometry_available':True}).sort('feed.fetched_at',1):
                if projected<=OBJECT_BUDGET_BYTES:break
                if archive['_id'] in protected:continue
                self.manifests.update_one({'_id':archive['_id']},{'$set':{'geometry_available':False,'geometry_retention_reason':'STORAGE_BUDGET'}});evicted+=1
                self._gc(extra=added)
                known={row['_id']:row['compressed_bytes'] for row in self.objects.find({}, {'compressed_bytes':1})}
                added={c['hash']:c['compressed_bytes'] for c in manifest['chunks'] if c['hash'] not in known}
                projected=sum(known.values())+sum(added.values())
            if projected>OBJECT_BUDGET_BYTES:raise CandidateError('COMPRESSED_STORAGE_BUDGET_EXCEEDED')
            if check_database:
                stats=self.db.command('dbStats',scale=1)
                if stats.get('dataSize',0)+stats.get('indexSize',0)+sum(added.values())+len(added)*1024>DATABASE_CEILING_BYTES:raise CandidateError('DATABASE_STORAGE_BUDGET_EXCEEDED')
            generation=manifest['_id'];promoted=False
            try:
                for descriptor in manifest['chunks']:
                    if descriptor['hash'] in known:continue
                    packed=(directory/(descriptor['hash']+'.gz')).read_bytes()
                    self.objects.update_one({'_id':descriptor['hash']},{'$setOnInsert':{'payload':Binary(packed),'compressed_bytes':len(packed),'raw_bytes':descriptor['raw_bytes'],'created_at':utc_now()}},upsert=True)
                required={c['hash'] for c in manifest['chunks']}
                if self.objects.count_documents({'_id':{'$in':list(required)}})!=len(required):raise RuntimeError('Compressed object write incomplete')
                self.manifests.insert_one({**manifest,'state':'STAGED','published_at':utc_now(),'archive_evicted_count':evicted})
                if replaces_generation:previous=active.get('previous')
                elif active and active.get('storage_version') in VERSIONS:previous={k:active[k] for k in ('storage_version','active_generation','record_count','feature_count')}
                else:previous=active
                self.control.replace_one({'_id':key},{'_id':key,'source_id':'gistda','product_id':product(window),'storage_version':manifest['storage_version'],
                    'active_generation':generation,'record_count':len(manifest['chunks']),'feature_count':manifest['feed']['record_count'],'previous':previous,
                    'revision':int((active or {}).get('revision',0))+1,'published_at':utc_now()},upsert=True)
                promoted=True
                self.manifests.update_one({'_id':generation},{'$set':{'state':'PUBLISHED'}})
                if replaces_generation:
                    # Keep old cached/pinned pages readable during the bounded migration grace.
                    retire=(datetime.now(timezone.utc)+timedelta(seconds=REPACK_GRACE_SECONDS)).isoformat().replace('+00:00','Z')
                    self.manifests.update_one({'_id':replaces_generation},{'$set':{'replaced_by':generation,'retire_after':retire}})
                self._gc()
                return {'active_generation':generation,'feature_count':manifest['feed']['record_count'],'record_count':len(manifest['chunks']),
                        'compressed_bytes':manifest['compressed_bytes'],'archive_evicted_count':evicted}
            except Exception:
                if not promoted:self.manifests.delete_one({'_id':generation});self._gc()
                raise

    def _verify_objects(self,manifest,deep=True):
        descriptors={c['hash']:c for c in manifest['chunks']};seen=set()
        query={'_id':{'$in':list(descriptors)}}
        for row in self.objects.find(query,None if deep else {'payload':0}).batch_size(20 if deep else 500):
            descriptor=descriptors[row['_id']]
            if row.get('compressed_bytes')!=descriptor['compressed_bytes'] or row.get('raw_bytes')!=descriptor['raw_bytes']:raise ValueError('Stored flood size mismatch')
            if deep:checked_payload(descriptor,bytes(row['payload']),manifest['storage_version'])
            seen.add(row['_id'])
        if len(seen)!=len(descriptors):raise ValueError('Missing compressed flood object')

    def verify(self,window,deep=True):
        pointer=self.control.find_one({'_id':'gistda:'+product(window)})
        if not pointer or pointer.get('storage_version') not in VERSIONS:return None
        manifest=self.manifests.find_one({'_id':pointer['active_generation']})
        if not manifest or not manifest.get('geometry_available') or manifest['feed']['record_count']!=pointer['feature_count'] or len(manifest['chunks'])!=pointer['record_count']:raise ValueError('Invalid compressed flood pointer')
        validate_manifest(manifest);self._verify_objects(manifest,deep)
        count=sum(c['count'] for c in manifest['chunks'])
        if count!=pointer['feature_count']:raise ValueError('Incomplete compressed flood generation')
        return {'source_id':'gistda','product_id':product(window),'status':'VERIFIED','active_records':count,'stored_chunks':len(manifest['chunks']),'storage_version':manifest['storage_version']}

    def repack(self,window,directory,check_database=True):
        pointer=self.control.find_one({'_id':'gistda:'+product(window)})
        if not pointer or pointer.get('storage_version') not in VERSIONS:raise ValueError('No compressed flood product to repack')
        original=self.manifests.find_one({'_id':pointer['active_generation']});validate_manifest(original)
        if original['storage_version']==CURRENT_VERSION:return {'window':window,'status':'ALREADY_ENCODED'}
        candidate=deepcopy(original);candidate.update(_id=str(uuid4()),storage_version=CURRENT_VERSION,
            query_identity=original.get('query_identity',original['_id']),repacked_from=original['_id'],repacked_at=utc_now())
        for key in ['state','published_at','archive_evicted_count','replaced_by','retire_after']:candidate.pop(key,None)
        rewritten={};descriptors={c['hash']:c for c in original['chunks']}
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        for row in self.objects.find({'_id':{'$in':list(descriptors)}}).batch_size(20):
            descriptor=descriptors[row['_id']]
            rows=checked_payload(descriptor,bytes(row['payload']),original['storage_version']);raw,packed=pack_rows(rows)
            # Same Python numeric types, values and ordering before changing any pointer.
            if encoded(unpacked(raw,CURRENT_VERSION))!=encoded(rows):raise ValueError('Repack changed original normalized values')
            digest=hashlib.sha256(raw).hexdigest();(directory/(digest+'.gz')).write_bytes(packed)
            rewritten[row['_id']]={**descriptor,'hash':digest,'raw_bytes':len(raw),'compressed_bytes':len(packed)}
        if len(rewritten)!=len(descriptors):raise ValueError('Missing repack source object')
        chunks=[rewritten[c['hash']] for c in original['chunks']]
        candidate.update(chunks=chunks,compressed_bytes=sum(c['compressed_bytes'] for c in chunks))
        result=self.publish(candidate,directory,check_database=check_database,replaces_generation=original['_id'])
        self.db.source_status.update_one({'_id':'gistda:'+product(window)},{'$set':{'storage_version':CURRENT_VERSION,
            'active_generation':result['active_generation'],'compressed_bytes':result['compressed_bytes'],'storage_maintenance_at':utc_now()}})
        return {**result,'window':window,'status':'REPACKED','old_bytes':original['compressed_bytes'],'new_bytes':candidate['compressed_bytes'],
                'stored_chunks':result['record_count'],'record_count':original['feed']['record_count'],'fetched_at':original['feed']['fetched_at']}

    def rollback(self,window='3days'):
        with self.lock():
            key='gistda:'+product(window);active=self.control.find_one({'_id':key}) or {};previous=active.get('previous')
            if not previous:raise ValueError('No retained generation for rollback')
            old={k:active[k] for k in ('storage_version','active_generation','record_count','feature_count')} if active.get('storage_version') in VERSIONS else {
                k:active[k] for k in ('source_id','product_id','active_slot','active_run_id','record_count','feature_count','chunk_count','completeness','scope_area_id') if k in active}
            if previous.get('active_slot') in ('A','B'):
                from .chunks import check_chunks
                rows=list(self.db.satellite_flood_3days_latest.find({'slot':previous['active_slot'],'etl_run_id':previous['active_run_id']},{'_id':0,'slot':0,'etl_run_id':0}))
                check_chunks(rows)
                self.control.replace_one({'_id':key},{**previous,'_id':key,'previous':old,'revision':int(active.get('revision',0))+1,'published_at':utc_now()});return
            if previous.get('storage_version') not in VERSIONS:raise ValueError('Unsupported rollback generation')
            # Check all old objects before an atomic pointer change.
            manifest=self.manifests.find_one({'_id':previous['active_generation']})
            if not manifest or not manifest.get('geometry_available'):raise ValueError('Retained generation unavailable')
            validate_manifest(manifest);self._verify_objects(manifest,True)
            self.control.replace_one({'_id':key},{'_id':key,'source_id':'gistda','product_id':product(window),**previous,'previous':old,'published_at':utc_now(),'revision':int(active.get('revision',0))+1})
