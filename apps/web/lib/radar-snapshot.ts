import 'server-only';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {mongoDatabase,mongoUri} from './mongo';
import {emptyRadar,radarFreshness,radarKey,validatedRadar,type RadarSnapshot} from './radar';
let cache:{until:number;value:RadarSnapshot}|null=null;
export async function readRadarSnapshot():Promise<RadarSnapshot>{
  if(cache&&cache.until>Date.now())return {...cache.value,freshness:radarFreshness(cache.value.feed)};
  let result:RadarSnapshot={...emptyRadar};
  try{
    if(mongoUri()){
      result.storage='mongo';const db=await mongoDatabase();
      for(let i=0;i<3;i++){
        const pointer=await db.collection('snapshot_control').findOne({_id:radarKey as never},{maxTimeMS:5000});
        if(!pointer)break;
        if(!['A','B'].includes(pointer.active_slot)||pointer.record_count!==1)throw Error('Invalid radar pointer');
        const row=await db.collection('radar_latest').findOne({source_id:'tmd_radar',product_id:'composite_rain_rate',slot:pointer.active_slot,etl_run_id:pointer.active_run_id},{projection:{_id:0,slot:0,etl_run_id:0},maxTimeMS:5000});
        if(row){result.feed=validatedRadar(row);break;}
        if(i===2)throw Error('Radar generation changed');
      }
      const status=await db.collection('source_status').findOne({_id:radarKey as never},{maxTimeMS:5000});
      if(status)result.health=Object.fromEntries(['last_attempt','last_success','completed_at','status','last_result','frame_count','latest_observed_at','quality_issue_count','run_url','failure_stage','error_type','blob_upload_reserved','blob_upload_remaining','blob_upload_limit'].map(key=>[key,status[key]??null]));
    }else if(process.env.NODE_ENV!=='production'&&process.env.HAZARD_LOCAL_SNAPSHOT==='1'){
      const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/radar-capture.json'),'utf8'));
      const frames=payload.frames.map(({observed_at,sha256,byte_length,width,height}:{observed_at:string;sha256:string;byte_length:number;width:number;height:number})=>({observed_at,sha256,byte_length,width,height,url:'/api/radar/frame/'+sha256}));
      result={...result,storage:'local',feed:validatedRadar({...payload,frames},true),health:{status:'SUCCESS',last_attempt:payload.fetched_at,last_success:payload.fetched_at}};
    }
    result.freshness=radarFreshness(result.feed);
  }catch{result={...emptyRadar,storage:mongoUri()?'mongo':'unconfigured',error:'Radar snapshot temporarily unavailable'};}
  cache={until:Date.now()+(result.error?10000:30000),value:result};return result;
}
