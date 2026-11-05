'use client';
import {useState} from 'react';
import {ArrowLeft,ArrowUpRight,Satellite} from 'lucide-react';
import type {Area,FloodSnapshot,Freshness,FloodWindow} from '@/lib/types';
import {areaById} from '@/lib/geography';
import {bangkokTime} from '@/lib/semantics';
import {floodInArea,floodRecordsInArea,floodScopeLabel,floodWindowText,floodRefreshFailure,floodResultCount} from '@/lib/floods';
import {viewportStatusText} from '@/lib/flood-viewport';
import type {FloodViewportState} from './use-flood-viewport';

type Props={area:Area;snapshot:FloodSnapshot;queryFreshness:Freshness;selectedId:string|null;
  onSelect:(id:string|null)=>void;onArea:(id:string)=>void;window:FloodWindow;onWindow:(window:FloodWindow)=>void;
  generation:string;onGeneration:(value:string)=>void;onPage:(value:number)=>void;displayMode?:'viewport'|'area';onDisplayMode?:(value:'viewport'|'area')=>void;viewport?:FloodViewportState};
export default function FloodPanel({area,snapshot,queryFreshness,selectedId,onSelect,onArea,window,onWindow,generation,onGeneration,onPage,displayMode='area',onDisplayMode,viewport}:Props){
  const [visibleCount,setVisibleCount]=useState(100);
  const feed=snapshot.feed,inScope=floodInArea(area,feed),rows=displayMode==='viewport'?(viewport?.records??[]):floodRecordsInArea(snapshot,area);
  const selected=rows.findIndex(row=>row.id===selectedId);
  const refreshFailure=floodRefreshFailure(snapshot.health);
  const count=floodResultCount(snapshot,area),summary=snapshot.scope?.mode==='summary'||snapshot.presentation==='summary';
  const label=floodWindowText(window),page=snapshot.pagination;
  return <section className="dam-evidence flood-evidence" aria-label="GISTDA flood observations">
    <div className="dam-heading"><Satellite size={16}/><b>Flood observations</b><span className={`freshness ${queryFreshness.toLowerCase()}`}>QUERY {queryFreshness}</span></div>
    <p className="dam-source-caption">GISTDA Disaster Platform · {label}</p>
    <label>ช่วงข้อมูลย้อนหลัง <select aria-label="GISTDA product window" value={window} onChange={e=>onWindow(e.target.value as FloodWindow)}>
      {(['3days','7days','30days'] as const).map(w=><option key={w} value={w} disabled={w!=='3days'&&w!==window&&!snapshot.window_catalog?.some(c=>c.window===w)}>{w==='3days'?'3 วัน · มุมมองหลัก':w==='7days'?'7 วัน · ข้อมูลย้อนหลัง':'30 วัน · ข้อมูลย้อนหลัง'}</option>)}
    </select></label>
    {onDisplayMode&&<label>ขอบเขตบนแผนที่ <select aria-label="GISTDA map loading mode" value={displayMode} onChange={e=>onDisplayMode(e.target.value as 'viewport'|'area')}>
      <option value="viewport">ตามบริเวณที่มองเห็น</option><option value="area">รายการของพื้นที่ที่เลือก</option>
    </select></label>}
    {!!snapshot.query_history?.length&&<label>ชุดที่ดึงจาก API <select aria-label="GISTDA query snapshot" value={generation} onChange={e=>onGeneration(e.target.value)}>
      <option value="">ชุดล่าสุดที่ดึง</option>{snapshot.query_history.map(h=><option key={h.generation} value={h.generation}>{bangkokTime(h.fetched_at)} · {h.record_count.toLocaleString()} รูปพื้นที่{h.geometry_available?'':' · เหลือข้อมูลสรุป'}</option>)}
    </select></label>}
    <h3>{floodScopeLabel(feed)}{feed&&' · ประเทศไทย'}</h3>
    <p className="flood-note">ยังไม่ทราบสถานะน้ำท่วมปัจจุบัน · ข้อมูลนี้เป็นรูปพื้นที่จากผลิตภัณฑ์ย้อนหลัง ไม่ยืนยันว่าขณะนี้ยังท่วมหรือน้ำลด เวลาถ่ายดาวเทียมและพื้นที่ที่ภาพใช้ได้ยังไม่ระบุ แยกจากเวลาเรียก API</p>
    {(window!=='3days'||snapshot.historical_query)&&<p className="flood-note">ข้อมูลอ้างอิงย้อนหลัง · ไม่ใช่น้ำท่วมต่อเนื่อง {window.replace('days','')} วัน และไม่ใช้แทนข้อมูลใหม่ของพื้นที่อื่น</p>}
    {refreshFailure&&<p className="failed-run" role="status">{refreshFailure} {feed?'Retaining the last complete product query; its timestamps appear below.':'No complete product query is available.'} No partial result was published.</p>}
    {!feed?<p className="flood-note">{snapshot.error??'Awaiting a published GISTDA product snapshot.'}</p>:<>
      {snapshot.storage==='local'&&<p className="flood-note">LOCAL QA PREVIEW · not a production observation.</p>}
      {!inScope?<p className="flood-note">The selected area is outside this product's supported scope. No flood result is available for this area.</p>:
        count===0?<p className="flood-note">No returned features for {area.name_th} in the completed provider query. This does not establish no flooding, complete satellite coverage or safe conditions.</p>:
        <p className="flood-note">{count??'—'} provider footprints for {area.name_th}. Their acquisition age is unknown; they are not a live-water or water-depth map.</p>}
      {displayMode==='viewport'&&viewport&&inScope&&<p className="flood-note" role="status">{viewportStatusText(viewport.status,rows.length,viewport.matched_count)} · กรอบค้นหาไม่ใช่ขอบเขตการตรวจวัดดาวเทียม และไม่คำนวณพื้นที่น้ำท่วม</p>}
      {summary&&<p className="flood-note">{displayMode==='viewport'?'จำนวนด้านบนเป็นของพื้นที่ที่เลือก · ซูมหรือเลื่อนแผนที่เพื่อโหลดขอบเขตบริเวณที่ต้องการ':'แสดงสรุปจำนวนรูปพื้นที่ · เปิดเลเยอร์และเลือกจังหวัด/อำเภอเพื่อดูขอบเขต ชุดใหญ่จะแบ่งตามพื้นที่'} · ไม่ระบายทั้งจังหวัดเป็นน้ำท่วม</p>}
      {snapshot.presentation==='metadata_only'&&<p className="flood-note">ชุดประวัตินี้เหลือข้อมูลสรุป ขอบเขตภาพหมดช่วงเก็บตามงบพื้นที่จัดเก็บ จึงไม่แสดงรูปพื้นที่จากชุดอื่นมาทดแทน</p>}
      {!!snapshot.child_areas?.length&&summary&&<div className="dam-list">{snapshot.child_areas.map(child=><button key={child.area_id} onClick={()=>onArea(child.area_id)}><span>{areaById.get(child.area_id)?.name_th??child.area_id}<small>{child.record_count.toLocaleString()} รูปพื้นที่จากผลิตภัณฑ์นี้</small></span><ArrowUpRight size={12}/></button>)}</div>}
      <button className="dam-back" onClick={()=>onArea(feed.area_id)}>Open Thailand <ArrowUpRight size={12}/></button>
      <dl className="dam-details"><dt>Product window</dt><dd>{label}</dd><dt>Satellite acquired</dt><dd>Not supplied · age unknown</dd>
        <dt>API response</dt><dd>{bangkokTime(feed.response_at)}</dd><dt>Retrieved</dt><dd>{bangkokTime(feed.fetched_at)}</dd>
        <dt>Query completeness</dt><dd>All {feed.record_count} reported results · {feed.page_count} page(s), unfiltered</dd><dt>Selected area results</dt><dd>{inScope?count??'Loading':'Outside scope'}</dd><dt>Area / depth metrics</dt><dd>Not calculated</dd></dl>
      {inScope&&rows.length>0&&(selected>=0?<><button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> All returned footprints</button>
        <p className="flood-note">Footprint {selected+1} of {rows.length}. No feature acquisition timestamp or area metric is supplied.</p></>:
        <><div className="dam-list">{rows.slice(0,visibleCount).map((row,index)=><button key={row.id} onClick={()=>onSelect(row.id)}><span>Provider footprint {index+1}<small>Acquisition time not supplied</small></span><ArrowUpRight size={13}/></button>)}</div>
        {rows.length>visibleCount&&<button className="dam-back" onClick={()=>setVisibleCount(count=>count+100)}>Show 100 more ({visibleCount} of {rows.length})</button>}</>)}
      {displayMode==='area'&&snapshot.presentation==='page'&&page&&<div><p className="flood-note">แสดงเฉพาะหน้า {page.chunk+1}/{page.chunk_count} · {rows.length} จาก {count?.toLocaleString()} รูปพื้นที่ ขอบเขตบนแผนที่เป็นของหน้านี้เท่านั้น</p>
        <button disabled={page.chunk===0} onClick={()=>onPage(page.chunk-1)}>หน้าก่อนหน้า</button> <button disabled={page.next_chunk===null} onClick={()=>onPage(page.chunk+1)}>หน้าถัดไป</button></div>}
      {snapshot.health?.last_failure_at&&<p className="flood-note">เคยเก็บไม่สำเร็จ {bangkokTime(String(snapshot.health.last_failure_at))} · {String(snapshot.health.last_failure_reason??'UNKNOWN')} · เก็บประวัตินี้ไว้แม้รอบต่อมาสำเร็จ</p>}
      {typeof snapshot.health?.consecutive_empty_queries==='number'&&snapshot.health.consecutive_empty_queries>0&&<p className="flood-note">ผลค้นว่าง {snapshot.health.consecutive_empty_queries} รอบต่อเนื่อง · ไม่ใช้สรุปว่าไม่มีน้ำท่วมหรือดาวเทียมยังไม่ผ่าน</p>}
      {!!snapshot.recent_runs?.length&&<details><summary>ประวัติรอบเก็บล่าสุด</summary>{snapshot.recent_runs.map((run,i)=><p key={i}>{bangkokTime(run.completed_at)} · {run.status} · {run.record_count??run.provider_number_matched??'—'} รูปพื้นที่ {run.error_summary??''}</p>)}</details>}
      {queryFreshness!=='FRESH'&&<p className="flood-note">The query is {queryFreshness.toLowerCase()}; any displayed footprints are gray references from the last completed snapshot.</p>}
      <p className="dam-note">The weather forecast date does not change this product's window or timestamps. Administrative filtering does not certify satellite coverage or exact polygon clipping. Pagination checks counts and duplicates; the provider supplies no snapshot version token.</p>
    </>}
    <a className="source-link" href="https://disaster.gistda.or.th/services/open-api" target="_blank" rel="noreferrer">GISTDA product documentation <ArrowUpRight size={12}/></a>
  </section>;
}
