import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedWarningFeed} from './contracts';
import {warningFreshness} from './warnings';
import type {WarningFeed,WarningSnapshot} from './types';
let cache:{until:number;value:WarningSnapshot}|null=null;
const key='tmd:cap_warnings';
function metadata(feed:WarningFeed|null){if(!feed)return null;const {records,...meta}=feed;return meta;}
export async function readWarningSnapshot():Promise<WarningSnapshot>{
  if(cache&&cache.until>Date.now())return cache.value;
  let result:WarningSnapshot={feed:null,records:[],health:null,freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase();let feed:WarningFeed|null=null;
      for(let attempt=0;attempt<3;attempt++){
        const pointer=await db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000});
        if(!pointer)break;
        if(pointer.record_count!==1||!['A','B'].includes(pointer.active_slot))throw new Error('Invalid CAP snapshot pointer');
        const row=await db.collection('agency_warning_latest').findOne({source_id:'tmd',product_id:'cap_warnings',snapshot_id:'latest',slot:pointer.active_slot,
          etl_run_id:pointer.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000});
        if(row){feed=validatedWarningFeed(row);break;}
        if(attempt===2)throw new Error('CAP snapshot changed during read');
      }
      const status=await db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000});
      const health=status?Object.fromEntries(['status','last_attempt','last_success','completed_at','record_count','feed_item_count','ignored_item_count','completeness'].map(k=>[k,status[k]??null])):null;
      if(health)health.error_summary=status?.status==='FAILED'?status.error_summary??null:null;
      result={...result,feed:metadata(feed),records:feed?.records??[],health,freshness:warningFreshness(feed)};
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const value=JSON.parse(await readFile(path.join(process.cwd(),'data/local/warnings.json'),'utf-8'));
      const feed=validatedWarningFeed(value.feed);
      result={feed:metadata(feed),records:feed.records,health:value.status??null,storage:'local',error:null,freshness:warningFreshness(feed)};
    }
  }catch{
    result={feed:null,records:[],health:null,freshness:'UNAVAILABLE',storage:mongoUri()?'mongo':'unconfigured',error:'TMD CAP snapshot is temporarily unavailable'};
  }
  result.freshness=warningFreshness(result.feed,Date.now(),result.health?.status==='FAILED');
  cache={until:Date.now()+(result.error?10000:60000),value:result};return result;
}
