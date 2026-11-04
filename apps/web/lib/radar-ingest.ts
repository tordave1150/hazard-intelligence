import 'server-only';
import {randomUUID} from 'node:crypto';
import {put,del} from '@vercel/blob';
import {mongoDatabase} from './mongo';
import {radarKey,validatedRadar,type RadarManifest} from './radar';
import {decodedRadarCandidate} from './radar-capture';
import {reserveRadarUploads} from './radar-budget';

type Run={run_id:string;run_attempt:string;issued_at:number;run_url:string};

export async function publishRadar(value:unknown,run:Run){
  const failed=!!value&&typeof value==='object'&&Object.keys(value).length===1&&(value as {capture_failed?:unknown}).capture_failed===true;
  const candidate=failed?null:decodedRadarCandidate(value);
  const db=await mongoDatabase(),locks=db.collection('etl_locks'),control=db.collection('snapshot_control'),records=db.collection('radar_latest'),statuses=db.collection('source_status');
  const token=randomUUID(),now=new Date().toISOString();
  try{await locks.insertOne({_id:radarKey as never,token,started_at:now});}catch(error){if((error as {code?:number}).code===11000)return {status:'BUSY',frame_count:0};throw Error('Radar publication lock unavailable');}
  const uploaded:string[]=[];let promoted=false,stage='CHECK_PREVIOUS';
  try{
    const priorStatus=await statuses.findOne({_id:radarKey as never});
    if(priorStatus?.last_oidc_issued_at&&Number(priorStatus.last_oidc_issued_at)>run.issued_at)throw Error('Older ingestion request');
    if(priorStatus?.last_run_id===run.run_id&&priorStatus?.last_run_attempt===run.run_attempt&&priorStatus.status==='SUCCESS')return {status:'ALREADY_PUBLISHED',frame_count:priorStatus.frame_count};
    await statuses.updateOne({_id:radarKey as never},{$set:{source_id:'tmd_radar',product_id:'composite_rain_rate',last_attempt:now,status:'RUNNING',run_url:run.run_url,last_run_id:run.run_id,last_run_attempt:run.run_attempt,last_oidc_issued_at:run.issued_at}}, {upsert:true});
    if(!candidate){stage='SOURCE_CAPTURE';throw Error('Source capture failed');}
    await records.createIndex({source_id:1,product_id:1,slot:1,snapshot_id:1},{unique:true});
    const active=await control.findOne({_id:radarKey as never});
    const oldRows=await records.find({source_id:'tmd_radar',product_id:'composite_rain_rate'},{projection:{_id:0},maxTimeMS:5000}).limit(3).toArray();
    if(oldRows.length>2)throw Error('Radar retention exceeded');
    const activeFeed=oldRows.find(row=>row.slot===active?.active_slot&&row.etl_run_id===active?.active_run_id);
    if(activeFeed&&Date.parse(candidate.feed.frames.at(-1)!.observed_at)<Date.parse((activeFeed.frames as RadarManifest['frames']).at(-1)!.observed_at)){
      const difference=Date.parse((activeFeed.frames as RadarManifest['frames']).at(-1)!.observed_at)-Date.parse(candidate.feed.frames.at(-1)!.observed_at);
      if((activeFeed.sampling_minutes??15)===15&&difference===900000){
        // The first half-hour sample may trail the old quarter-hour feed. Keep its clock/pointer.
        await statuses.updateOne({_id:radarKey as never},{$set:{status:'SUCCESS',completed_at:new Date().toISOString(),last_result:'WAITING_FOR_NEXT_SAMPLE'},$unset:{failure_stage:'',error_type:'',error_summary:''}});
        return {status:'WAITING_FOR_NEXT_SAMPLE',frame_count:activeFeed.frames.length};
      }
      throw Error('Radar observation regressed');
    }
    const pending=Array.isArray(priorStatus?.cleanup_pending)?priorStatus.cleanup_pending.filter((url:unknown)=>typeof url==='string'&&/^https:\/\/[a-z0-9]+\.public\.blob\.vercel-storage\.com\/tmd-radar\//.test(url)):[];
    if(pending.length>52)throw Error('Radar cleanup requires recovery before new uploads');
    const known=new Map(oldRows.flatMap(row=>(row.frames as RadarManifest['frames']).map(frame=>[frame.observed_at+'|'+frame.sha256,frame.url] as const)));
    stage='BLOB_BUDGET';
    const needed=candidate.feed.frames.filter(frame=>!known.has(frame.observed_at+'|'+frame.sha256)).length;
    const budget=reserveRadarUploads(priorStatus?.blob_upload_reservations,needed);
    // Persist before PUT while holding the publication lock. Failed/uncertain uploads stay reserved.
    await statuses.updateOne({_id:radarKey as never},{$set:{blob_upload_reservations:budget.reservations,blob_upload_reserved:budget.reserved,blob_upload_remaining:budget.remaining,blob_upload_limit:budget.limit}});
    const frames=[];stage='BLOB_UPLOAD';
    for(const frame of candidate.feed.frames){
      let url=known.get(frame.observed_at+'|'+frame.sha256);
      if(!url){
        const pathname='tmd-radar/'+frame.observed_at.replace(/[-:]/g,'')+'-'+frame.sha256+'.png';
        const object=await put(pathname,candidate.images.get(frame.sha256)!,{access:'public',addRandomSuffix:false,allowOverwrite:false,contentType:'image/png',cacheControlMaxAge:86400});
        url=object.url;uploaded.push(url);
      }
      frames.push({...frame,url});
    }
    const feed=validatedRadar({...candidate.feed,frames}),slot=active?.active_slot==='A'?'B':'A',generation=randomUUID();
    stage='METADATA_WRITE';
    await records.deleteMany({slot});await records.insertOne({...feed,slot,etl_run_id:generation});
    const previous=active?{active_slot:active.active_slot,active_run_id:active.active_run_id,record_count:1}:null;
    stage='POINTER_PROMOTION';
    await control.replaceOne({_id:radarKey as never},{_id:radarKey as never,source_id:'tmd_radar',product_id:'composite_rain_rate',active_slot:slot,active_run_id:generation,record_count:1,previous,published_at:now,revision:Number(active?.revision??0)+1},{upsert:true});
    promoted=true;stage='CLEANUP';
    const keep=new Set([...frames.map(frame=>frame.url),...(activeFeed?.frames as RadarManifest['frames']??[]).map(frame=>frame.url)]);
    const obsolete=[...new Set([...pending,...oldRows.flatMap(row=>(row.frames as RadarManifest['frames']).map(frame=>frame.url)).filter(url=>!keep.has(url))])].filter(url=>!keep.has(url));
    let cleanupFailed=false;
    try{if(obsolete.length)await del(obsolete);}catch{cleanupFailed=true;}
    await statuses.updateOne({_id:radarKey as never},{$set:{status:'SUCCESS',last_result:'PUBLISHED',completed_at:new Date().toISOString(),last_success:now,frame_count:frames.length,
      latest_observed_at:frames.at(-1)!.observed_at,active_generation:generation,quality_issue_count:cleanupFailed?1:0,cleanup_pending:cleanupFailed?obsolete:[],
      requested_locations:1,successful_locations:1,completeness:1},$unset:{error_summary:'',failure_stage:'',error_type:''}});
    return {status:'SUCCESS',frame_count:frames.length};
  }catch(error){
    console.error('radar_publication_failed',{stage,error_type:error instanceof Error?error.name:'Error'});
    if(!promoted&&uploaded.length){try{await del(uploaded);}catch{await statuses.updateOne({_id:radarKey as never},{$addToSet:{cleanup_pending:{$each:uploaded}}});}}
    await statuses.updateOne({_id:radarKey as never},{$set:{status:'FAILED',last_result:'FAILED',completed_at:new Date().toISOString(),failure_stage:stage,error_type:error instanceof Error?error.name:'Error',error_summary:'Radar capture or publication failed; last complete generation remains available'}},{upsert:true});
    throw Error('Radar publication failed');
  }finally{await locks.deleteOne({_id:radarKey as never,token});}
}
