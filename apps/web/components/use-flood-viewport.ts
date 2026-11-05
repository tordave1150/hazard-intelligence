'use client';
import {useEffect,useState} from 'react';
import type {FloodSnapshot,FloodWindow} from '@/lib/types';
import {loadFloodViewport} from '@/lib/flood-viewport-client';
import {validFloodBounds,type FloodBounds,type FloodMapView,type FloodViewport} from '@/lib/flood-viewport';
export type FloodViewportState={status:string;records:FloodViewport['records'];matched_count:number|null;complete:boolean};
const noRecords:FloodViewport['records']=[];
export function useFloodViewport(enabled:boolean,window:FloodWindow,areaId:string,snapshot:FloodSnapshot,view:FloodMapView|null,refresh:number):FloodViewportState{
  const [state,setState]=useState<{key:string;value:FloodViewportState}|null>(null);
  const generation=snapshot.pagination?.generation??'',fetchedAt=snapshot.feed?.fetched_at??'',sourceCount=snapshot.feed?.record_count??0;
  // Only the query envelope is rounded outward; original geometry is never rounded.
  const bbox=view?[Math.floor(view.bbox[0]*10000)/10000,Math.floor(view.bbox[1]*10000)/10000,Math.ceil(view.bbox[2]*10000)/10000,Math.ceil(view.bbox[3]*10000)/10000] as FloodBounds:null;
  const supported=snapshot.feed?.schema_version==='3.0'&&snapshot.feed.product_window===window;
  const boxKey=bbox?.join(',')??'',ready=enabled&&supported&&!!generation&&!!fetchedAt&&!!view?.settled&&view.zoom>=8&&!!bbox&&validFloodBounds(bbox)&&bbox[0]<bbox[2]&&bbox[1]<bbox[3];
  const key=[window,areaId,generation,boxKey,refresh,ready].join('|');
  useEffect(()=>{
    if(!ready)return;
    const controller=new AbortController();let active=true;
    const load=()=>loadFloodViewport(controller.signal,{window,areaId,generation,bbox:boxKey.split(',').map(Number) as FloodBounds,fetchedAt,sourceCount})
      .then(value=>{if(active)setState({key,value});}).catch(()=>{if(active&&!controller.signal.aborted)setState({key,value:{status:'FAILED',records:[],matched_count:null,complete:false}});});
    const delay=setTimeout(load,250),timer=setInterval(load,60000);
    return()=>{active=false;controller.abort();clearTimeout(delay);clearInterval(timer);};
  },[ready,key,boxKey,window,areaId,generation,fetchedAt,sourceCount]);
  if(!enabled)return {status:'DISABLED',records:noRecords,matched_count:null,complete:false};
  if(snapshot.feed&&snapshot.feed.schema_version!=='3.0')return {status:'INDEX_UNAVAILABLE',records:noRecords,matched_count:null,complete:false};
  if(supported&&snapshot.scope?.area_id===areaId&&snapshot.scope.record_count===0)return {status:'EMPTY',records:noRecords,matched_count:0,complete:true};
  if(!view?.settled)return {status:'MOVING',records:noRecords,matched_count:null,complete:false};
  if(view.zoom<8||!bbox||!validFloodBounds(bbox)||bbox[0]===bbox[2]||bbox[1]===bbox[3])return {status:'ZOOM_REQUIRED',records:noRecords,matched_count:null,complete:false};
  return state?.key===key?state.value:{status:'LOADING',records:noRecords,matched_count:null,complete:false};
}
