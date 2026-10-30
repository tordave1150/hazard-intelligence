'use client';
import {useMemo,useState} from 'react';
import {ArrowLeft,ArrowUpRight,CloudRain,Search} from 'lucide-react';
import type {Area,RainSnapshot,Freshness} from '@/lib/types';
import {gaugeInArea,gaugeName,gaugeValue,gaugeWallTime} from '@/lib/gauges';
import {areaById} from '@/lib/geography';
import {bangkokTime} from '@/lib/semantics';
export default function RainPanel({area,snapshot,freshness,selectedId,onSelect}:{area:Area;snapshot:RainSnapshot;freshness:Freshness;selectedId:string|null;onSelect:(id:string|null)=>void}){
  const [search,setSearch]=useState(''),[limit,setLimit]=useState(100);
  const rows=useMemo(()=>snapshot.records.filter(r=>gaugeInArea(r,area)),[snapshot.records,area]);
  const selected=rows.find(r=>r.gauge_id===selectedId),matches=rows.filter(r=>`${gaugeName(r)} ${r.station_code??''} ${r.gauge_id}`.toLowerCase().includes(search.toLowerCase()));
  return <section className="dam-evidence gauge-evidence" aria-label="HII observed rain stations"><div className="dam-heading"><CloudRain size={16}/><b>Observed rain stations</b><span className={`freshness ${freshness.toLowerCase()}`}>QUERY {freshness}</span></div>
    <p className="dam-source-caption">HII / ThaiWater · ฝนตรวจวัดตามต้นทาง</p>
    {!snapshot.feed?<p className="dam-empty">{snapshot.error??'ยังไม่มีชุดฝนที่เผยแพร่'}</p>:!snapshot.detail_loaded?<p role="status">{snapshot.error??'กำลังอ่านรายละเอียดสถานีฝนทั้งประเทศ…'}</p>:<>
      {snapshot.storage==='local'&&<p className="flood-note">LOCAL QA PREVIEW · ไม่ใช่ข้อมูล production</p>}
      <p className="gauge-time-note">เวลาสถานีไม่ระบุเขตเวลา จึงยังไม่ยืนยันอายุการตรวจวัดและเวลาต้น–ปลายช่วงสะสมใน UTC จุดสีน้ำเงินระบุประเภทสถานีฝน ไม่ใช่ระดับความเสี่ยง</p>
      {selected?<><button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> กลับรายการสถานีฝน</button><h3>{gaugeName(selected)}</h3><p className="dam-id">{selected.station_code??selected.source_station_id} · {selected.agency_name??'ไม่ระบุหน่วยงานผู้วัด'}</p>
        <div className="gauge-level">{gaugeValue(selected.rain_24h_mm)}<small>mm / 24h · ฝนสะสม 24 ชั่วโมงตามต้นทาง</small></div>
        <dl className="dam-details"><dt>ฝน 1 ชั่วโมงตามต้นทาง</dt><dd>{gaugeValue(selected.rain_1h_mm)} mm / 1h</dd><dt>เวลาตรวจวัดต้นฉบับ</dt><dd>{gaugeWallTime(selected.source_observed_at)}</dd>
          <dt>ดึงชุดข้อมูล</dt><dd>{bangkokTime(snapshot.feed.fetched_at)}</dd><dt>จังหวัด / อำเภอ</dt><dd>{areaById.get(selected.province_id)?.name_th} / {selected.district_id?areaById.get(selected.district_id)?.name_th:'ยังจับคู่ไม่ได้'}</dd>
          <dt>การจับคู่อำเภอ</dt><dd>{selected.district_mapping==='UNCONFIRMED'?'ยังไม่ยืนยัน':'ชื่อไทยตรงกันเพียงแห่งเดียวภายในจังหวัดต้นทาง'}</dd>
          <dt>ลุ่มน้ำ</dt><dd>{selected.basin_id?areaById.get(selected.basin_id)?.name_th:'ยังไม่ยืนยันจากขอบเขต'}</dd><dt>คุณภาพรายการ</dt><dd>{selected.quality_flags.length?selected.quality_flags.join(', '):'ผ่านรูปแบบข้อมูล · ยังไม่รับรองการวัด'}</dd></dl>
      </>:<><p className="dam-report-date">{area.name_th} · {rows.length} สถานีฝนในคำตอบชุดนี้</p><label className="gauge-search"><Search size={13}/><input aria-label="ค้นหาสถานีฝนตรวจวัด" placeholder="ชื่อหรือรหัสสถานีฝน" value={search} onChange={e=>{setSearch(e.target.value);setLimit(100);}}/></label>
        <div className="dam-list">{matches.slice(0,limit).map(r=><button key={r.gauge_id} onClick={()=>onSelect(r.gauge_id)}><span>{gaugeName(r)}<small>{gaugeValue(r.rain_24h_mm)} mm / 24h · {r.source_observed_at??'ไม่ระบุเวลา'} · เขตเวลาไม่ระบุ</small></span><ArrowUpRight size={13}/></button>)}</div>
        {!matches.length&&<p className="dam-empty">ไม่มีรายการตรงกับพื้นที่หรือคำค้นในชุดนี้ การไม่มีรายการไม่หมายถึงไม่มีฝน</p>}
        {matches.length>limit&&<button className="dam-back" onClick={()=>setLimit(n=>n+100)}>แสดงอีก 100 สถานีฝน ({limit}/{matches.length})</button>}
        <dl className="dam-details"><dt>ชุดประเทศ</dt><dd>{snapshot.feed.record_count} สถานีฝน · {snapshot.feed.coverage_by_province.length} จังหวัด</dd><dt>ดึงล่าสุด</dt><dd>{bangkokTime(snapshot.feed.fetched_at)}</dd><dt>รหัสนอกจังหวัดไทย</dt><dd>{snapshot.feed.excluded_stations.length} รายการ</dd></dl></>}
      {(snapshot.error||snapshot.health?.status==='FAILED')&&<p className="failed-run">อ่านหรืออัปเดตรอบล่าสุดไม่สำเร็จ แสดงชุดที่สำเร็จก่อนหน้า</p>}
      <p className="dam-note">ค่า 0 คือค่าที่รายงานจริง ค่าขาดแสดง “ไม่ระบุ” เป็นข้อมูลจุดสถานี ไม่ใช่ฝนเฉลี่ยทั้งจังหวัด และแยกจากพยากรณ์ Open-Meteo</p>
    </>}
    <a className="source-link" href="https://www.thaiwater.net/weather/rainfall" target="_blank" rel="noreferrer">ThaiWater และหน่วยงานผู้วัด <ArrowUpRight size={12}/></a>
  </section>;
}
