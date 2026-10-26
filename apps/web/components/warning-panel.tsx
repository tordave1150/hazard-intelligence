'use client';
import {useState} from 'react';
import {ArrowLeft,ArrowUpRight,Radio} from 'lucide-react';
import {bangkokTime} from '@/lib/semantics';
import {warningInArea,warningState} from '@/lib/warnings';
import type {Area,WarningSnapshot,Freshness} from '@/lib/types';
type Props={snapshot:WarningSnapshot;freshness:Freshness;area:Area;areas:Area[];selectedId:string|null;now:number;onSelect:(id:string|null)=>void};
export default function WarningPanel({snapshot,freshness,area,areas,selectedId,now,onSelect}:Props){
  const [previous,setPrevious]=useState(false);
  const scoped=snapshot.records.filter(r=>warningInArea(r,area,areas));
  const visible=scoped.filter(r=>previous||['CURRENT','UPCOMING','TIME_UNKNOWN'].includes(warningState(r,snapshot.records,now)));
  const selected=snapshot.records.find(r=>r.warning_id===selectedId);
  const current=scoped.filter(r=>warningState(r,snapshot.records,now)==='CURRENT').length;
  return <section className="warning-evidence" aria-label="TMD CAP messages">
    <div className="dam-heading"><Radio size={16}/><b>Agency warnings</b><span className={`freshness ${freshness.toLowerCase()}`} title="Feed freshness, separate from message validity">FEED {freshness}</span></div>
    <p className="dam-source-caption">กรมอุตุนิยมวิทยา · TMD CAP feed</p>
    {!snapshot.feed?<p>{snapshot.error?'TMD messages are temporarily unavailable.':'Awaiting the first published CAP snapshot.'}</p>:selected?<>
      <button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> Back to CAP messages</button>
      <span className="warning-state">{warningState(selected,snapshot.records,now)==='CURRENT'&&freshness!=='FRESH'?'VALIDITY WINDOW · CURRENCY UNVERIFIED':warningState(selected,snapshot.records,now)}</span>
      <h3>{selected.headline??selected.message_type}</h3><p className="dam-id">{selected.warning_id}</p>
      <dl className="dam-details"><dt>Issued by TMD</dt><dd>{bangkokTime(selected.issued_at)}</dd>
        <dt>Effective</dt><dd>{bangkokTime(selected.effective_start)}</dd><dt>Expires</dt><dd>{bangkokTime(selected.expires_at)}</dd>
        <dt>Agency severity</dt><dd>{selected.agency_severity??'Not supplied'}</dd>
        <dt>Urgency / certainty</dt><dd>{selected.urgency??'—'} / {selected.certainty??'—'}</dd>
        <dt>Message type</dt><dd>{selected.message_type}</dd><dt>Retrieved</dt><dd>{bangkokTime(selected.fetched_at)}</dd></dl>
      {warningState(selected,snapshot.records,now)!=='CURRENT'&&<p className="warning-archive-note">Previous or non-current message · gray outlines are for reference and are not a current warning area.</p>}
      <p className="warning-original">{selected.description}</p>{selected.instruction&&<p className="warning-original">{selected.instruction}</p>}
      {selected.source_areas.map((a,i)=><p className="dam-note" key={i}>TMD area description: {a.description}</p>)}
      <a className="source-link" href={selected.content_ref} target="_blank" rel="noreferrer">Original TMD CAP message <ArrowUpRight size={12}/></a>
    </>:<>
      <p className="dam-report-date">{current} messages within their issued validity window in this feed.</p>
      {!current&&<p className="warning-archive-note">No unexpired CAP message in the latest feed for this area. This does not establish safe conditions or complete warning coverage.</p>}
      <label className="check-line"><input type="checkbox" checked={previous} onChange={e=>setPrevious(e.target.checked)}/> Show previous feed messages ({scoped.length})</label>
      <div className="dam-list">{visible.map(row=><button key={row.warning_id} onClick={()=>onSelect(row.warning_id)}><span>{row.headline??row.message_type}<small>{warningState(row,snapshot.records,now)} · {bangkokTime(row.issued_at)}</small></span><ArrowUpRight size={13}/></button>)}</div>
    </>}
    {snapshot.feed&&<p className="dam-note">Feed checked {bangkokTime(snapshot.feed.fetched_at)}. Feed freshness measures retrieval, not warning issuance. The weather forecast timeline does not change these times. Province references are not district-specific warnings; outlines preserve TMD's published polygons.</p>}
    {freshness!=='FRESH'&&snapshot.feed&&<p className="warning-archive-note">Feed is {freshness.toLowerCase()}; current coverage is unverified. Colored warning outlines are paused.</p>}
    {snapshot.health?.status==='FAILED'&&<p className="failed-run">Latest TMD refresh failed · showing the last complete feed.</p>}
  </section>;
}
