'use client';
import {ArrowLeft,ArrowUpRight,Satellite} from 'lucide-react';
import type {Area,FloodSnapshot,Freshness} from '@/lib/types';
import {bangkokTime} from '@/lib/semantics';
import {floodInArea,floodRecordsInArea,floodScopeLabel,floodWindowLabel,floodRefreshFailure} from '@/lib/floods';

type Props={area:Area;snapshot:FloodSnapshot;queryFreshness:Freshness;selectedId:string|null;
  onSelect:(id:string|null)=>void;onArea:(id:string)=>void};
export default function FloodPanel({area,snapshot,queryFreshness,selectedId,onSelect,onArea}:Props){
  const feed=snapshot.feed,inScope=floodInArea(area,feed),rows=floodRecordsInArea(snapshot,area);
  const selected=rows.findIndex(row=>row.id===selectedId),national=feed?.area_id==='TH';
  const refreshFailure=floodRefreshFailure(snapshot.health);
  return <section className="dam-evidence flood-evidence" aria-label="GISTDA flood observations">
    <div className="dam-heading"><Satellite size={16}/><b>Flood observations</b><span className={`freshness ${queryFreshness.toLowerCase()}`}>QUERY {queryFreshness}</span></div>
    <p className="dam-source-caption">GISTDA Disaster Platform · {floodWindowLabel}</p>
    <h3>{floodScopeLabel(feed)}{feed&&` · ${national?'ประเทศไทย':'องครักษ์'}`}</h3>
    <p className="flood-note">{feed&&(national?'All results from the unfiltered previous one-day product query; province and district views use the supplied administrative codes.':'The retained pilot is limited to the provider district query for Ongkharak.')} This is a retrospective product; the exact observation date and satellite acquisition time are not supplied in this feed.</p>
    {refreshFailure&&<p className="failed-run" role="status">{refreshFailure} {feed?'Retaining the last complete product query; its timestamps appear below.':'No complete product query is available.'} No partial result was published.</p>}
    {!feed?<p className="flood-note">{snapshot.error??'Awaiting a published GISTDA product snapshot.'}</p>:<>
      {snapshot.storage==='local'&&<p className="flood-note">LOCAL QA PREVIEW · not a production observation.</p>}
      {!inScope?<p className="flood-note">The selected area is outside this product's supported scope. No flood result is available for this area.</p>:
        rows.length===0?<p className="flood-note">No returned features for {area.name_th} in the completed provider query. This does not establish no flooding, complete satellite coverage or safe conditions.</p>:
        <p className="flood-note">{rows.length} provider footprints for {area.name_th}. Their acquisition age is unknown; they are not a live-water or water-depth map.</p>}
      <button className="dam-back" onClick={()=>onArea(feed.area_id)}>Open {national?'Thailand':'Ongkharak'} <ArrowUpRight size={12}/></button>
      <dl className="dam-details"><dt>Product window</dt><dd>{floodWindowLabel}</dd><dt>Satellite acquired</dt><dd>Not supplied · age unknown</dd>
        <dt>API response</dt><dd>{bangkokTime(feed.response_at)}</dd><dt>Retrieved</dt><dd>{bangkokTime(feed.fetched_at)}</dd>
        <dt>Query completeness</dt><dd>All {feed.record_count} reported results · {national?`${feed.page_count} page(s), unfiltered`:'one district query'}</dd><dt>Selected area results</dt><dd>{inScope?rows.length:'Outside scope'}</dd><dt>Area / depth metrics</dt><dd>Not calculated</dd></dl>
      {inScope&&rows.length>0&&(selected>=0?<><button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> All returned footprints</button>
        <p className="flood-note">Footprint {selected+1} of {rows.length}. No feature acquisition timestamp or area metric is supplied.</p></>:
        <div className="dam-list">{rows.map((row,index)=><button key={row.id} onClick={()=>onSelect(row.id)}><span>Provider footprint {index+1}<small>Acquisition time not supplied</small></span><ArrowUpRight size={13}/></button>)}</div>)}
      {queryFreshness!=='FRESH'&&<p className="flood-note">The query is {queryFreshness.toLowerCase()}; any displayed footprints are gray references from the last completed snapshot.</p>}
      <p className="dam-note">The weather forecast date does not change this product's window or timestamps. Administrative filtering does not certify satellite coverage or exact polygon clipping.{national?' Pagination checks counts and duplicates; the provider supplies no snapshot version token.':''}</p>
    </>}
    <a className="source-link" href="https://disaster.gistda.or.th/services/open-api" target="_blank" rel="noreferrer">GISTDA product documentation <ArrowUpRight size={12}/></a>
  </section>;
}
