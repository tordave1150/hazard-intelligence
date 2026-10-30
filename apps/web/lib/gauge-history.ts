import 'server-only';
import {parseGaugeHistory,wallOrdinal} from './gauge-history-data';
import type {GaugeHistory,GaugeStation} from './types';
const source='https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_graph';
const cache=new Map<string,{until:number;value:GaugeHistory}>();
const pending=new Map<string,Promise<GaugeHistory>>();
export async function readGaugeHistory(station:GaugeStation):Promise<GaugeHistory>{
  if(!station.source_observed_at)throw Error('Station has no reported date');
  const ordinal=wallOrdinal(station.source_observed_at),end=station.source_observed_at.slice(0,10),start=new Date(ordinal-2*86400000).toISOString().slice(0,10);
  const key=station.gauge_id+':'+end,cached=cache.get(key);
  if(cached&&cached.until>Date.now())return cached.value;
  if(pending.has(key))return pending.get(key)!;
  if(pending.size>=8)throw Error('Station history is busy');
  const promise=(async()=>{
    const query=new URLSearchParams({station_type:'tele_waterlevel',station_id:station.source_station_id,start_date:start,end_date:end});
    const response=await fetch(source+'?'+query,{cache:'no-store',redirect:'error',credentials:'omit',signal:AbortSignal.timeout(15000),headers:{Accept:'application/json'}});
    if(!response.ok)throw Error('Station history is unavailable');
    if(!response.body)throw Error('Missing station history body');
    const reader=response.body.getReader(),chunks:Uint8Array[]=[];let size=0;
    try{
      while(true){const {done,value}=await reader.read();if(done)break;
        size+=value.byteLength;if(size>2*1024*1024)throw Error('Station history exceeds size limit');chunks.push(value);}
    }finally{await reader.cancel().catch(()=>{});}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
    const value=parseGaugeHistory(JSON.parse(new TextDecoder().decode(bytes)),{gauge_id:station.gauge_id,source_id:'thaiwater',
      unit:'m above mean sea level',observation_time_status:'TIMEZONE_NOT_SUPPLIED',fetched_at:new Date().toISOString(),start_date:start,end_date:end,source_url:source});
    if(cache.size>=64)cache.delete(cache.keys().next().value!);
    cache.set(key,{until:Date.now()+900000,value});return value;
  })();
  pending.set(key,promise);
  try{return await promise;}finally{pending.delete(key);}
}
