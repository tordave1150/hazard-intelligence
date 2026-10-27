'use client';
import {ArrowLeft,ArrowUpRight,Satellite} from 'lucide-react';
import type {Area,FloodSnapshot,Freshness} from '@/lib/types';
import {bangkokTime} from '@/lib/semantics';
import {floodInArea,floodScopeId} from '@/lib/floods';

type Props={area:Area;snapshot:FloodSnapshot;queryFreshness:Freshness;selectedId:string|null;
  onSelect:(id:string|null)=>void;onArea:(id:string)=>void};
export default function FloodPanel({area,snapshot,queryFreshness,selectedId,onSelect,onArea}:Props){
  const inScope=floodInArea(area),feed=snapshot.feed;
  const selected=snapshot.records.findIndex(row=>row.id===selectedId);
  return <section className="dam-evidence flood-evidence" aria-label="GISTDA flood observations">
    <div className="dam-heading"><Satellite size={16}/><b>Flood observations</b><span className={`freshness ${queryFreshness.toLowerCase()}`}>QUERY {queryFreshness}</span></div>
    <p className="dam-source-caption">GISTDA Disaster Platform · 1day product</p>
    <h3>Ongkharak pilot · องครักษ์</h3>
    <p className="flood-note">Coverage is limited to the provider query for {floodScopeId}. Satellite acquisition time is not supplied.</p>
    {!feed?<p className="flood-note">{snapshot.error??'Awaiting the first published GISTDA district snapshot.'}</p>:<>
      {snapshot.storage==='local'&&<p className="flood-note">LOCAL QA PREVIEW · not a production observation.</p>}
      {!inScope?<p className="flood-note">The selected area is outside this pilot scope. No flood result is available for this area.</p>:
        snapshot.records.length===0?<p className="flood-note">The completed provider query returned no features. This does not establish no flooding, complete satellite coverage or safe conditions.</p>:
        <p className="flood-note">{snapshot.records.length} provider footprints returned. Their acquisition age is unknown; they are not a live-water or water-depth map.</p>}
      <button className="dam-back" onClick={()=>onArea(floodScopeId)}>Open Ongkharak <ArrowUpRight size={12}/></button>
      <dl className="dam-details"><dt>Product window</dt><dd>1day · provider label</dd><dt>Satellite acquired</dt><dd>Not supplied · age unknown</dd>
        <dt>API response</dt><dd>{bangkokTime(feed.response_at)}</dd><dt>Retrieved</dt><dd>{bangkokTime(feed.fetched_at)}</dd>
        <dt>Query completeness</dt><dd>All {feed.record_count} reported results · one district query</dd><dt>Area / depth metrics</dt><dd>Not calculated</dd></dl>
      {inScope&&snapshot.records.length>0&&(selected>=0?<><button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> All returned footprints</button>
        <p className="flood-note">Footprint {selected+1} of {snapshot.records.length}. No feature acquisition timestamp or area metric is supplied.</p></>:
        <div className="dam-list">{snapshot.records.map((row,index)=><button key={row.id} onClick={()=>onSelect(row.id)}><span>Provider footprint {index+1}<small>Acquisition time not supplied</small></span><ArrowUpRight size={13}/></button>)}</div>)}
      {queryFreshness!=='FRESH'&&<p className="flood-note">The query is {queryFreshness.toLowerCase()}; any displayed footprints are gray references from the last completed snapshot.</p>}
      {snapshot.health?.status==='FAILED'&&<p className="failed-run">Latest GISTDA refresh failed · retaining the last complete district query.</p>}
      <p className="dam-note">The weather forecast date does not change this product's window or timestamps. Provider district filtering does not certify satellite coverage or exact polygon clipping.</p>
    </>}
    <a className="source-link" href="https://disaster.gistda.or.th/services/open-api" target="_blank" rel="noreferrer">GISTDA product documentation <ArrowUpRight size={12}/></a>
  </section>;
}
