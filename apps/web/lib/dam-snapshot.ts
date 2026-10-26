import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedDam} from './contracts';
import {damFreshness,damMetadata} from './dams';
import type {DamSnapshot} from './types';
let cache:{until:number;value:DamSnapshot}|null=null;
const key='rid:daily_dam_storage';
export async function readDamSnapshot():Promise<DamSnapshot>{
  if(cache&&cache.until>Date.now())return cache.value;
  let result:DamSnapshot={records:[],health:null,freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
  try{
    if(mongoUri()){
      result.storage='mongo';
      const db=await mongoDatabase();
      let records:DamSnapshot['records']|null=null;
      for(let i=0;i<3;i++){
        const control=await db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000});
        if(!control){records=[];break;}
        if(control.record_count!==damMetadata.length)throw new Error('Invalid dam snapshot coverage');
        const rows=await db.collection('dam_latest').find({source_id:'rid',product_id:'daily_dam_storage',
          slot:control.active_slot,etl_run_id:control.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000}).limit(100).toArray();
        if(rows.length===control.record_count){records=rows.map(validatedDam);break;}
      }
      if(!records)throw new Error('Dam snapshot changed during query');
      const status=await db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000});
      const health=status?Object.fromEntries(['last_attempt','last_success','completed_at','status','completeness','successful_locations','requested_locations','report_date'].map(k=>[k,status[k]??null])):null;
      if(health)health.error_summary=status?.status==='FAILED'?status.error_summary??null:null;
      result={...result,records,health,freshness:damFreshness(records)};
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/dams.json'),'utf-8'));
      if(!Array.isArray(payload.records)||payload.records.length!==damMetadata.length)throw new Error('Incomplete local dam reports');
      const records=payload.records.map(validatedDam);
      result={records,health:payload.status??null,storage:'local',error:null,freshness:damFreshness(records)};
    }
    if(result.records.length&&(new Set(result.records.map(r=>r.dam_id)).size!==damMetadata.length||new Set(result.records.map(r=>r.report_date)).size!==1))throw new Error('Invalid dam identity or date coverage');
  }catch{
    result={records:[],health:null,freshness:'UNAVAILABLE',storage:mongoUri()?'mongo':'unconfigured',error:'RID report snapshot is temporarily unavailable'};
  }
  cache={until:Date.now()+(result.error?10000:60000),value:result};
  return result;
}
