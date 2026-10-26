'use client';
import {ArrowLeft,ArrowUpRight,Droplets} from 'lucide-react';
import {bangkokTime} from '@/lib/semantics';
import {damInArea,reportDate} from '@/lib/dams';
import type {Area,DamSnapshot,Freshness} from '@/lib/types';
type Props={area:Area;snapshot:DamSnapshot;freshness:Freshness;selectedId:string|null;onSelect:(id:string)=>void;onClose:()=>void};
const volume=(value:number|null)=>value===null?'Not provided':`${value.toLocaleString('en-GB',{maximumFractionDigits:2})} million m³`;
export default function DamPanel({area,snapshot,freshness,selectedId,onSelect,onClose}:Props){
  const records=snapshot.records.filter(d=>damInArea(d,area));
  const dam=snapshot.records.find(d=>d.dam_id===selectedId);
  return <section className="dam-evidence" aria-label="RID reservoir reports">
    <div className="dam-heading"><Droplets size={16}/><b>Reservoir reports</b><span className={`freshness ${freshness.toLowerCase()}`}>{freshness}</span></div>
    <p className="dam-source-caption">RID · daily reported observations</p>
    {!snapshot.records.length?<p className="dam-empty">{snapshot.error?'RID reports are temporarily unavailable.':'Awaiting the first published RID report.'}</p>:dam?<>
      <button className="dam-back" onClick={onClose}><ArrowLeft size={12}/> Back to reservoir list</button>
      <h3>{dam.name_th}</h3><p className="dam-id">{dam.source_dam_id} · {dam.owner}</p>
      <div className="dam-percent">{dam.storage_pct===null?'—':dam.storage_pct.toFixed(2)+'%'}<span>of normal storage capacity</span></div>
      <dl className="dam-details"><dt>Reported water volume</dt><dd>{volume(dam.storage_volume_mcm)}</dd>
        <dt>Normal capacity</dt><dd>{volume(dam.normal_capacity_mcm)}</dd><dt>Maximum capacity</dt><dd>{volume(dam.maximum_capacity_mcm)}</dd>
        <dt>Report date</dt><dd>{reportDate(dam.report_date)}</dd><dt>Observation time</dt><dd>Not supplied · date only</dd>
        <dt>Retrieved</dt><dd>{bangkokTime(dam.fetched_at)}</dd><dt>Quality</dt><dd>{dam.quality_status}</dd></dl>
      <p className="dam-note">Percentages can exceed 100% of normal capacity. They describe reservoir storage and do not indicate flood depth or downstream hazard.</p>
      <a className="source-link" href={dam.metadata_url} target="_blank" rel="noreferrer">RID source report <ArrowUpRight size={12}/></a>
    </>:<>
      <p className="dam-report-date">Report: {reportDate(snapshot.records[0].report_date)} · {records.length} in this area</p>
      {records.length?<div className="dam-list">{records.map(d=><button key={d.dam_id} onClick={()=>onSelect(d.dam_id)}><span>{d.name_th}<small>{d.storage_pct===null?'No volume percentage':`${d.storage_pct.toFixed(2)}% of normal capacity`}</small></span><ArrowUpRight size={13}/></button>)}</div>:
        <p className="dam-empty">No monitored RID large-dam point is located in this area.</p>}
    </>}
    {snapshot.records.length>0&&<p className="dam-note">Reservoir reports keep their own date when the weather forecast timeline changes. Locations identify dam points; reservoir extents and downstream influence can cross area boundaries.</p>}
    {snapshot.health?.status==='FAILED'&&<p className="failed-run">Latest RID refresh failed · showing the last published report.</p>}
  </section>;
}
