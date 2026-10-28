import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {validatedHourly} from './contracts';
import {hourlyFreshness} from './hourly';
import {areas} from './geography';
import type {HourlySnapshot} from './types';
let cached:{until:number;value:HourlySnapshot}|null=null;
export async function readHourlySnapshot():Promise<HourlySnapshot>{
  if(cached&&cached.until>Date.now())return cached.value;
  let result:HourlySnapshot={records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE'};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase(),key='open_meteo:today_hourly';
      const expected=areas.filter(a=>a.level==='province'||a.level==='district').map(a=>a.id);
      let complete=false;
      for(let attempt=0;attempt<3;attempt++){
        const control=await db.collection('snapshot_control').findOne({_id:key as never},{maxTimeMS:5000});
        if(!control){complete=true;break;}
        if(control.record_count!==expected.length||!['A','B'].includes(control.active_slot))throw Error('Invalid hourly pointer');
        const rows=await db.collection('weather_hourly_latest').find({source_id:'open_meteo',product_id:'today_hourly',slot:control.active_slot,etl_run_id:control.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000}).limit(expected.length+1).toArray();
        if(rows.length!==expected.length)continue;
        result.records=rows.map(validatedHourly);
        if(new Set(result.records.map(r=>r.location_id)).size!==expected.length||new Set(result.records.map(r=>r.forecast_date)).size!==1)throw Error('Incomplete hourly coverage');
        complete=true;break;
      }
      if(!complete)throw Error('Hourly generation changed');
      const status=await db.collection('source_status').findOne({_id:key as never},{maxTimeMS:5000});
      result.health=status?Object.fromEntries(['status','last_attempt','last_success','completed_at','forecast_date','record_count'].map(k=>[k,status[k]??null])):null;
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/hourly.json'),'utf8'));
      if(!Array.isArray(payload.records)||payload.records.length>1005)throw Error('Invalid local hourly snapshot');
      result={...result,records:payload.records.map(validatedHourly),health:payload.status??null,storage:'local'};
    }
  }catch{result={records:[],health:null,storage:mongoUri()?'mongo':'unconfigured',error:'Hourly forecast is unavailable; daily forecasts remain independent.',freshness:'UNAVAILABLE'};}
  result.freshness=hourlyFreshness(result.records,Date.now(),result.health?.status==='FAILED');
  cached={until:Date.now()+(result.error?10000:60000),value:result};return result;
}
