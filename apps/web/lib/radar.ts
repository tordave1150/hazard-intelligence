import Ajv from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from '../../../packages/contracts/radar.schema.json';
import type {Freshness} from './types';

export type RadarFrame={observed_at:string;sha256:string;byte_length:number;width:1800;height:2644;url:string};
export type RadarManifest={schema_version:'2.0';source_id:'tmd_radar';product_id:'composite_rain_rate';data_state:'radar_estimate';snapshot_id:'latest';
  fetched_at:string;source_url:string;coordinates:number[][];units:'mm/hour';generation_consistency:string;sampling_minutes?:15|30;frames:RadarFrame[]};
export type RadarSnapshot={feed:RadarManifest|null;health:Record<string,unknown>|null;freshness:Freshness;storage:'mongo'|'local'|'unconfigured';error:string|null};
export type RadarLoad={id:string;status:'loading'|'loaded'|'error'};
export const radarCoordinates:[[number,number],[number,number],[number,number],[number,number]]=[[95,22.5],[108,22.5],[108,4],[95,4]];
export const radarKey='tmd_radar:composite_rain_rate';
export const emptyRadar:RadarSnapshot={feed:null,health:null,freshness:'UNAVAILABLE',storage:'unconfigured',error:null};
const ajv=new Ajv({strict:false});addFormats(ajv);const validate=ajv.compile<RadarManifest>(schema);
export function validatedRadar(value:unknown,local=false):RadarManifest{
  if(!validate(value))throw Error('Invalid radar manifest');
  const feed=value as RadarManifest,times=feed.frames.map(frame=>Date.parse(frame.observed_at)),fetched=Date.parse(feed.fetched_at);
  if(times.some((t,i)=>t%((feed.sampling_minutes??15)*60000)!==0||t>fetched+300000||i>0&&t<=times[i-1])||times.at(-1)!-times[0]>10800000||
    new Set(feed.frames.map(frame=>frame.url)).size!==feed.frames.length||feed.frames.reduce((n,f)=>n+f.byte_length,0)>2800000)throw Error('Invalid radar sequence');
  for(const frame of feed.frames){
    const leaf=frame.observed_at.replace(/[-:]/g,'')+'-'+frame.sha256+'.png';
    const remote=new RegExp('^https://[a-z0-9]+\\.public\\.blob\\.vercel-storage\\.com/tmd-radar/'+leaf.replaceAll('.','\\.')+'$');
    if(!remote.test(frame.url)&&!(local&&frame.url==='/api/radar/frame/'+frame.sha256))throw Error('Untrusted radar image URL');
  }
  return feed;
}
export function radarFreshness(feed:RadarManifest|null,now=Date.now()):Freshness{
  if(!feed?.frames.length)return 'UNAVAILABLE';
  const observed=Date.parse(feed.frames.at(-1)!.observed_at),fetched=Date.parse(feed.fetched_at);
  if(!Number.isFinite(observed)||!Number.isFinite(fetched)||observed>now+300000||fetched>now+300000)return 'UNKNOWN';
  const age=Math.max(now-observed,now-fetched);
  return age<=2700000?'FRESH':age<=5400000?'DELAYED':'STALE';
}
export const radarVisible=(freshness:Freshness)=>freshness==='FRESH'||freshness==='DELAYED';
export function radarMissingSlots(feed:RadarManifest){
  return Math.round((Date.parse(feed.frames.at(-1)!.observed_at)-Date.parse(feed.frames[0].observed_at))/((feed.sampling_minutes??15)*60000))+1-feed.frames.length;
}
// Provider image uses the same four geographic corners in its MapLibre viewer.
export function radarControlPixel(lon:number,lat:number){
  const y=(a:number)=>Math.log(Math.tan(Math.PI/4+a*Math.PI/360));
  return [(lon-95)/13*1800,(y(22.5)-y(lat))/(y(22.5)-y(4))*2644];
}
