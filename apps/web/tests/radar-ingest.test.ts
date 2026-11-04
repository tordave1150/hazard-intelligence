import {beforeEach,afterEach,describe,it,expect,vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {radarPng} from '../lib/radar-png';
const mocks=vi.hoisted(()=>({put:vi.fn(),del:vi.fn(),database:vi.fn()}));
vi.mock('@vercel/blob',()=>({put:mocks.put,del:mocks.del}));
vi.mock('../lib/mongo',()=>({mongoDatabase:mocks.database}));
import {publishRadar} from '../lib/radar-ingest';
const png=readFileSync(new URL('../../../tests/fixtures/radar/synthetic-transparent.png',import.meta.url)),checked=radarPng(png);
const frame={...checked,observed_at:'2026-11-04T12:30:00Z',path:'zr/24.png',image_base64:png.toString('base64')};
const capture={schema_version:'2.0',source_id:'tmd_radar',product_id:'composite_rain_rate',data_state:'radar_estimate',snapshot_id:'latest',
  fetched_at:'2026-11-04T12:46:00Z',source_url:'https://weather.tmd.go.th/composite/index_composite.html',coordinates:[[95,22.5],[108,22.5],[108,4],[95,4]],
  units:'mm/hour',generation_consistency:'MANIFEST_CLOCK_AND_DOUBLE_IMAGE_HASH_CHECKED_NO_VERSION_TOKEN',sampling_minutes:30,frames:[frame]};
const url=(time=frame.observed_at)=>'https://fixture.public.blob.vercel-storage.com/tmd-radar/'+time.replace(/[-:]/g,'')+'-'+checked.sha256+'.png';
const metadata=(time=frame.observed_at)=>({...checked,observed_at:time,url:url(time)});
const run={run_id:'1234',run_attempt:'1',issued_at:1793796360,run_url:'https://github.com/tordave1150/hazard-intelligence/actions/runs/1234'};

// In-memory boundary doubles record externally visible writes and injected failures.
function database(options:{reserved?:number;activeTime?:string;legacy?:boolean;metadataFailure?:boolean}={}){
  const health:Record<string,unknown>={status:'SUCCESS',last_success:'2026-11-04T12:20:00Z'};
  if(options.reserved!==undefined)health.blob_upload_reservations=[{day:'2026-11-04',count:options.reserved}];
  const previous=options.activeTime?{active_slot:'A',active_run_id:'old',record_count:1}:null;
  const rows=options.activeTime?[{...capture,frames:[metadata(options.activeTime)],sampling_minutes:options.legacy?undefined:30,slot:'A',etl_run_id:'old'}]:[];
  const writes:string[]=[];
  const control={findOne:vi.fn(async()=>previous),replaceOne:vi.fn(async()=>{writes.push('pointer');})};
  const records={createIndex:vi.fn(),find:vi.fn(()=>({limit:()=>({toArray:async()=>rows})})),deleteMany:vi.fn(),insertOne:vi.fn(async()=>{if(options.metadataFailure)throw Error('write failed');writes.push('metadata');})};
  const statuses={findOne:vi.fn(async()=>structuredClone(health)),updateOne:vi.fn(async(_filter,update)=>{
    if(update.$set){Object.assign(health,update.$set);if('blob_upload_reservations' in update.$set)writes.push('reserve');}
    for(const key of Object.keys(update.$unset??{}))delete health[key];
  })};
  const locks={insertOne:vi.fn(),deleteOne:vi.fn()};
  const collections={etl_locks:locks,snapshot_control:control,radar_latest:records,source_status:statuses};
  mocks.database.mockResolvedValue({collection:(name:keyof typeof collections)=>collections[name]});
  mocks.put.mockImplementation(async()=>{writes.push('put');return {url:url()};});
  mocks.del.mockResolvedValue(undefined);
  return {health,control,records,locks,writes};
}
beforeEach(()=>{vi.clearAllMocks();vi.useFakeTimers();vi.setSystemTime(new Date('2026-11-04T12:46:00Z'));vi.spyOn(console,'error').mockImplementation(()=>{});});
afterEach(()=>{vi.useRealTimers();vi.restoreAllMocks();});

describe('Radar publication preserves complete data across storage failures',()=>{
  it('persists reservations before PUT, then writes metadata and promotes the pointer',async()=>{
    const state=database();
    expect(await publishRadar(capture,run)).toEqual({status:'SUCCESS',frame_count:1});
    expect(state.writes).toEqual(['reserve','put','metadata','pointer']);
    expect(state.health.blob_upload_reserved).toBe(101);
    expect(state.health.status).toBe('SUCCESS');expect(state.locks.deleteOne).toHaveBeenCalledOnce();
  });
  it('reuses immutable images without reserving another upload',async()=>{
    const state=database({activeTime:frame.observed_at,reserved:1800});
    await publishRadar(capture,run);
    expect(mocks.put).not.toHaveBeenCalled();expect(state.health.blob_upload_reserved).toBe(1800);
    expect(state.control.replaceOne).toHaveBeenCalledOnce();
  });
  it('stops before uploading on exhausted budget and leaves the active pointer unchanged',async()=>{
    const state=database({activeTime:'2026-11-04T12:00:00Z',reserved:1800});
    await expect(publishRadar(capture,run)).rejects.toThrow();
    expect(mocks.put).not.toHaveBeenCalled();expect(state.control.replaceOne).not.toHaveBeenCalled();
    expect(state.health.failure_stage).toBe('BLOB_BUDGET');expect(state.health.last_success).toBe('2026-11-04T12:20:00Z');
  });
  it('keeps failed uploads reserved and reports the actual upload failure stage',async()=>{
    const state=database({reserved:10});mocks.put.mockRejectedValueOnce(Error('storage unavailable'));
    await expect(publishRadar(capture,run)).rejects.toThrow();
    expect(state.health.blob_upload_reserved).toBe(11);expect(state.health.failure_stage).toBe('BLOB_UPLOAD');
    expect(state.control.replaceOne).not.toHaveBeenCalled();expect(state.locks.deleteOne).toHaveBeenCalledOnce();
  });
  it('cleans newly uploaded objects if metadata fails without promoting the pointer',async()=>{
    const state=database({metadataFailure:true});
    await expect(publishRadar(capture,run)).rejects.toThrow();
    expect(mocks.del).toHaveBeenCalledWith([url()]);expect(state.control.replaceOne).not.toHaveBeenCalled();
    expect(state.health.failure_stage).toBe('METADATA_WRITE');
  });
  it('waits for the next sample during migration without moving the observation or success clock back',async()=>{
    const state=database({activeTime:'2026-11-04T12:45:00Z',legacy:true});
    expect(await publishRadar(capture,run)).toEqual({status:'WAITING_FOR_NEXT_SAMPLE',frame_count:1});
    expect(mocks.put).not.toHaveBeenCalled();expect(state.control.replaceOne).not.toHaveBeenCalled();
    expect(state.health.last_success).toBe('2026-11-04T12:20:00Z');expect(state.health.last_result).toBe('WAITING_FOR_NEXT_SAMPLE');
  });
  it('rejects regression after migration and reports capture failures separately',async()=>{
    const state=database({activeTime:'2026-11-04T13:00:00Z'});
    await expect(publishRadar(capture,run)).rejects.toThrow();
    expect(state.control.replaceOne).not.toHaveBeenCalled();expect(mocks.put).not.toHaveBeenCalled();
    await expect(publishRadar({capture_failed:true},run)).rejects.toThrow();
    expect(state.health.failure_stage).toBe('SOURCE_CAPTURE');
  });
});
