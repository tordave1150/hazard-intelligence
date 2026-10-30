import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedGaugeFeed} from './contracts';
import {gaugeQueryFreshness} from './gauges';
import {withBasin} from './basin-membership';
import type {GaugeFeed,GaugeSnapshot} from './types';
let cache:{until:number;value:GaugeSnapshot}|null=null;
const key='thaiwater:national_waterlevel';
function metadata(feed:GaugeFeed){const {records,...value}=feed;return value;}
export async function readGaugeSnapshot():Promise<GaugeSnapshot>{
  if(cache&&cache.until>Date.now())return cache.value;
  let result:GaugeSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase();let feed:GaugeFeed|null=null;
      for(let attempt=0;attempt<3;attempt++){
        const pointer=await db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000});
        if(!pointer)break;
        if(pointer.record_count!==1||!['A','B'].includes(pointer.active_slot))throw Error('Invalid station pointer');
        const row=await db.collection('gauge_latest').findOne({source_id:'thaiwater',product_id:'national_waterlevel',snapshot_id:'latest',slot:pointer.active_slot,etl_run_id:pointer.active_run_id},
          {projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000});
        if(row){feed=validatedGaugeFeed(row);break;}
        if(attempt===2)throw Error('Station generation changed');
      }
      const status=await db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000});
      const health=status?Object.fromEntries(['status','last_attempt','last_success','completed_at','record_count','provider_automatic_count','excluded_station_count',
        'manual_rows_not_used','province_count','quality_issue_count','time_unknown_count','scope_area_id','completeness','run_url','run_trigger','error_stage'].map(k=>[k,status[k]??null])):null;
      if(health)health.error_summary=status?.status==='FAILED'?status.error_summary??null:null;
      result={...result,feed:feed?metadata(feed):null,records:feed?.records??[],health};
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const value=JSON.parse(await readFile(path.join(process.cwd(),'data/local/gauges.json'),'utf8')),feed=validatedGaugeFeed(value.feed);
      result={...result,feed:metadata(feed),records:feed.records,health:value.status??null,storage:'local'};
    }
  }catch{result={...result,feed:null,records:[],health:null,error:'Station snapshot is temporarily unavailable'};}
  result.records=result.records.map(withBasin);
  result.freshness=result.feed?'UNKNOWN':'UNAVAILABLE';
  result.query_freshness=gaugeQueryFreshness(result.feed,Date.now(),result.health?.status==='FAILED');
  cache={until:Date.now()+(result.error?10000:60000),value:result};return result;
}
