import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {MongoClient} from 'mongodb';
import {validatedForecast} from './contracts';
import {freshness} from './semantics';
import type {Snapshot} from './types';
import {areaById} from './geography';

const globalMongo=globalThis as unknown as {hazardMongo?: Promise<MongoClient>};
let cached: {until: number; value: Snapshot} | null=null;
export function resetSnapshotCache() {cached=null;}
export async function readSnapshot(): Promise<Snapshot> {
  if(cached && cached.until>Date.now()) return cached.value;
  // Vercel's storage integration creates <CUSTOM_PREFIX>_URL. Keep the
  // original URI setting supported, with explicit URI taking precedence.
  const mongoUri=process.env.MONGODB_URI || process.env.MONGODB_URL;
  let result: Snapshot;
  try {
    if(mongoUri) {
      const connection = globalMongo.hazardMongo ??= new MongoClient(mongoUri,{
        maxPoolSize:5,serverSelectionTimeoutMS:5000,connectTimeoutMS:5000,socketTimeoutMS:10000
      }).connect().catch(error=>{globalMongo.hazardMongo=undefined;throw error;});
      const db=(await connection).db(process.env.MONGODB_DB_NAME || 'weather_db');
      let records: Snapshot['records'] | null=null;
      for(let attempt=0;attempt<3;attempt++) {
        const control=await db.collection('snapshot_control').findOne({_id:'open_meteo:daily_forecast' as never},{maxTimeMS:5000});
        if(!control) {records=[];break;}
        if(!Number.isInteger(control.record_count) || control.record_count>1200 || control.record_count<1) throw new Error('Invalid bounded snapshot');
        const raw=await db.collection('weather_latest').find({source_id:'open_meteo',product_id:'daily_forecast',
          slot:control.active_slot,etl_run_id:control.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000}).limit(1200).toArray();
        if(raw.length===control.record_count){records=raw.map(validatedForecast);break;}
      }
      if(!records) throw new Error('Snapshot changed during query');
      const status=await db.collection('source_status').findOne({_id:'open_meteo:daily_forecast' as never},{projection:{_id:0},maxTimeMS:5000});
      // Whitelist health output. Never return exception details, connection metadata or arbitrary database fields.
      const safeStatus=status ? Object.fromEntries(['last_attempt','last_success','completed_at','status','completeness','successful_locations','requested_locations','error_summary'].map(k=>[k,status[k]??null])) : null;
      result={records,status:safeStatus,storage:'mongo',error:null,freshness:freshness(records)};
    } else if(process.env.NODE_ENV!=='production' && process.env.HAZARD_LOCAL_SNAPSHOT==='1') {
      const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/weather.json'),'utf8'));
      if(!Array.isArray(payload.records) || payload.records.length>1200) throw new Error('Invalid local snapshot');
      const records=payload.records.map(validatedForecast);
      result={records,status:payload.status??null,storage:'local',error:null,freshness:freshness(records)};
    } else result={records:[],status:null,storage:'unconfigured',error:'Weather snapshot is not connected',freshness:'UNAVAILABLE'};
    if(result.records.some(r=>!areaById.has(r.location_id)) || new Set(result.records.map(r=>r.location_id)).size!==result.records.length) throw new Error('Invalid location coverage');
  } catch {
    result={records:[],status:null,storage:mongoUri?'mongo':'unconfigured',error:'Latest weather snapshot is temporarily unavailable',freshness:'UNAVAILABLE'};
  }
  cached={until:Date.now()+(result.error?10000:60000),value:result};
  return result;
}
