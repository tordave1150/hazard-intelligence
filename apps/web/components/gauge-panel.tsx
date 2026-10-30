'use client';
import {useEffect,useMemo,useState} from 'react';
import {ArrowLeft,ArrowUpRight,Search,Waves} from 'lucide-react';
import type {Area,GaugeHistory,GaugeSnapshot,Freshness} from '@/lib/types';
import {gaugeInArea,gaugeName,gaugeValue,gaugeWallTime} from '@/lib/gauges';
import {wallOrdinal} from '@/lib/gauge-history-data';
import {areaById} from '@/lib/geography';
import {bangkokTime} from '@/lib/semantics';

function StationHistory({id}:{id:string}){
  const [data,setData]=useState<GaugeHistory|null>(null),[failed,setFailed]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    fetch('/api/gauges/history?gauge_id='+encodeURIComponent(id),{signal:controller.signal,cache:'no-store'})
      .then(async response=>{if(!response.ok)throw Error();return response.json();})
      .then(value=>{if(active)setData(value);}).catch(()=>{if(active)setFailed(true);});
    return()=>{active=false;controller.abort();};
  },[id]);
  const chart=useMemo(()=>{
    if(!data)return null;
    const valid=data.points.filter(p=>p.value!==null);if(!valid.length)return null;
    const values=valid.map(p=>p.value!),low=Math.min(...values),high=Math.max(...values),pad=Math.max(.05,(high-low)*.1);
    const first=wallOrdinal(data.points[0].source_observed_at),last=wallOrdinal(data.points.at(-1)!.source_observed_at);
    const segments:string[]=[];let path:string[]=[];let prior:number|null=null;
    for(const point of data.points){
      const stamp=wallOrdinal(point.source_observed_at);
      if(point.value===null||prior!==null&&stamp-prior>5400000){if(path.length)segments.push(path.join(' '));path=[];}
      if(point.value!==null){
        const x=38+(stamp-first)/Math.max(1,last-first)*246,y=118-(point.value-low+pad)/(high-low+2*pad)*100;
        path.push(`${x.toFixed(1)},${y.toFixed(1)}`);prior=stamp;
      }else prior=null;
    }
    if(path.length)segments.push(path.join(' '));
    return {low,high,segments,valid,delta:valid.at(-1)!.value!-valid[0].value!};
  },[data]);
  return <section className="gauge-history" aria-label="ประวัติระดับน้ำรายสถานี"><h4>ประวัติระดับน้ำจากต้นทาง</h4>
    {!data?<p role="status">{failed?'ยังอ่านประวัติไม่ได้ ข้อมูลสถานีล่าสุดยังแสดงอยู่':'กำลังอ่านประวัติสถานี…'}</p>:<>
      <p>{data.start_date} – {data.end_date} · วันตามต้นทาง</p>
      {chart?<><svg viewBox="0 0 300 150" role="img" aria-label={`กราฟระดับน้ำ ${chart.valid.length} จุด หน่วยเมตรเทียบระดับทะเลปานกลาง`}>
        <line x1="38" y1="18" x2="38" y2="118" stroke="var(--line)"/><line x1="38" y1="118" x2="284" y2="118" stroke="var(--line)"/>
        <text x="3" y="26">{chart.high.toFixed(2)}</text><text x="3" y="118">{chart.low.toFixed(2)}</text>
        {chart.segments.map((points,i)=><polyline key={i} points={points} fill="none" stroke="var(--teal)" strokeWidth="2"/>)}
        <text x="38" y="137">{data.points[0].source_observed_at.slice(5,16)}</text><text x="284" y="137" textAnchor="end">{data.points.at(-1)!.source_observed_at.slice(5,16)}</text>
      </svg><p>{chart.valid.length} จุดที่มีค่า · เปลี่ยนจากจุดแรกถึงจุดสุดท้าย {chart.delta>0?'+':''}{chart.delta.toFixed(3)} ม.รทก.</p>
        <details><summary>ดูค่าตัวเลข 10 จุดล่าสุด</summary><table><thead><tr><th>เวลาต้นทาง</th><th>ม.รทก.</th></tr></thead><tbody>{chart.valid.slice(-10).map(p=><tr key={p.source_observed_at}><td>{p.source_observed_at}</td><td>{gaugeValue(p.value)}</td></tr>)}</tbody></table></details>
      </>:<p>ไม่มีค่าระดับน้ำที่ใช้วาดกราฟได้ในช่วงนี้</p>}
      <p>เวลายังไม่ระบุเขตเวลา เส้นขาดหมายถึงค่าที่ขาดหายหรือช่วงห่างเกิน 90 นาที กราฟแสดงประวัติของสถานี ไม่ใช่การคาดการณ์</p>
      {data.invalid_value_count>0&&<p>ค่าที่ไม่ผ่านรูปแบบ {data.invalid_value_count} จุด · แสดงเป็นช่องว่างในกราฟ</p>}
      <small>ดึงประวัติ {bangkokTime(data.fetched_at)} · เก็บแคชชั่วคราว 15 นาที กราฟอาจใหม่กว่าชุดแผนที่</small>
    </>}
  </section>;
}

type Props={area:Area;snapshot:GaugeSnapshot;queryFreshness:Freshness;selectedId:string|null;loading:boolean;
  onSelect:(id:string|null)=>void};
export default function GaugePanel({area,snapshot,queryFreshness,selectedId,loading,onSelect}:Props){
  const [search,setSearch]=useState(''),[limit,setLimit]=useState(100);
  const rows=useMemo(()=>snapshot.records.filter(row=>gaugeInArea(row,area)),[snapshot.records,area]);
  const matches=rows.filter(row=>`${gaugeName(row)} ${row.station_code??''} ${row.gauge_id}`.toLowerCase().includes(search.toLowerCase()));
  const selected=rows.find(row=>row.gauge_id===selectedId);
  return <section className="dam-evidence gauge-evidence" aria-label="HII ThaiWater river level stations">
    <div className="dam-heading"><Waves size={16}/><b>River level stations</b><span className={`freshness ${queryFreshness.toLowerCase()}`}>QUERY {queryFreshness}</span></div>
    <p className="dam-source-caption">HII / ThaiWater · ข้อมูลตรวจวัดตามต้นทาง</p>
    {!snapshot.feed?<p className="dam-empty">{loading?'กำลังอ่านสถานีทั้งประเทศ…':snapshot.error??'ยังไม่มีชุดสถานีที่เผยแพร่'}</p>:<>
      {snapshot.storage==='local'&&<p className="flood-note">LOCAL QA PREVIEW · ไม่ใช่ข้อมูล production</p>}
      <p className="gauge-time-note">เวลารายสถานีไม่ระบุเขตเวลา จึงยังยืนยันอายุข้อมูลไม่ได้ สีจุดเป็นกลางและไม่ได้บอกระดับความเสี่ยง</p>
      {selected?<>
        <button className="dam-back" onClick={()=>onSelect(null)}><ArrowLeft size={12}/> กลับรายการสถานี</button>
        <h3>{gaugeName(selected)}</h3><p className="dam-id">{selected.station_code??selected.source_station_id} · {selected.agency_name??'ไม่ระบุหน่วยงานผู้วัด'}</p>
        <div className="gauge-level">{gaugeValue(selected.water_level_msl)}<small>ม.รทก. · เมตรเทียบระดับทะเลปานกลาง</small></div>
        <dl className="dam-details"><dt>เวลาตรวจวัดต้นฉบับ</dt><dd>{gaugeWallTime(selected.source_observed_at)}</dd>
          <dt>เวลาตรวจวัด UTC</dt><dd>ยังไม่ยืนยัน</dd><dt>ดึงชุดข้อมูล</dt><dd>{bangkokTime(snapshot.feed.fetched_at)}</dd>
          <dt>ระดับน้ำหน่วยเมตร</dt><dd>{selected.water_level_m===null?'ไม่ระบุ':`${gaugeValue(selected.water_level_m)} m ตามต้นทาง`}</dd>
          <dt>จังหวัด / อำเภอ</dt><dd>{areaById.get(selected.province_id)?.name_th} / {selected.district_id?areaById.get(selected.district_id)?.name_th:'ยังจับคู่ไม่ได้'}</dd>
          <dt>ลุ่มน้ำ</dt><dd>{selected.basin_id?areaById.get(selected.basin_id)?.name_th:'ยังไม่ยืนยันจากขอบเขต'}</dd><dt>พิกัดสถานี</dt><dd>{selected.point?`${selected.point.lat.toFixed(5)}, ${selected.point.lon.toFixed(5)}`:'ไม่มีพิกัดที่ใช้บนแผนที่ได้'}</dd>
          <dt>คุณภาพรายการ</dt><dd>{selected.quality_flags.length?selected.quality_flags.join(', '):'ผ่านรูปแบบข้อมูล · ยังไม่ตรวจรับรองการวัด'}</dd></dl>
        <p className="dam-note">ม.รทก. เป็นระดับอ้างอิงทะเลปานกลาง ไม่ใช่ความลึกน้ำท่วม และไม่ควรเทียบค่าระหว่างสถานีเป็นอันดับความเสี่ยง</p>
        <StationHistory key={selected.gauge_id} id={selected.gauge_id}/>
      </>:<>
        <p className="dam-report-date">{area.name_th} · {rows.length} สถานีในคำตอบชุดนี้</p>
        <label className="gauge-search"><Search size={13}/><input aria-label="ค้นหาสถานีระดับน้ำ" value={search} placeholder="ชื่อหรือรหัสสถานี" onChange={event=>{setSearch(event.target.value);setLimit(100);}}/></label>
        {matches.length?<><div className="dam-list">{matches.slice(0,limit).map(row=><button key={row.gauge_id} onClick={()=>onSelect(row.gauge_id)}><span>{gaugeName(row)}<small>{gaugeValue(row.water_level_msl)} ม.รทก. · {row.source_observed_at??'ไม่ระบุเวลา'} · เขตเวลาไม่ระบุ</small></span><ArrowUpRight size={13}/></button>)}</div>
          {matches.length>limit&&<button className="dam-back" onClick={()=>setLimit(n=>n+100)}>แสดงอีก 100 สถานี ({limit}/{matches.length})</button>}</>:<p className="dam-empty">ไม่พบสถานีที่ตรงกับพื้นที่หรือคำค้นในชุดนี้ การไม่มีข้อมูลไม่ยืนยันสภาพน้ำปกติ</p>}
        <dl className="dam-details"><dt>ขอบเขตชุดประเทศ</dt><dd>{snapshot.feed.record_count} สถานี · {snapshot.feed.coverage_by_province.length} จังหวัดที่มีรายการ</dd>
          <dt>ดึงข้อมูลล่าสุด</dt><dd>{bangkokTime(snapshot.feed.fetched_at)}</dd><dt>รหัสพื้นที่ที่ไม่นับในไทย</dt><dd>{snapshot.feed.excluded_stations.length} รายการ</dd>
          <dt>รายการ manual แยกต่างหาก</dt><dd>{snapshot.feed.provider_manual_count} รายการ · ไม่รวมเป็นจุดระดับน้ำ</dd></dl>
      </>}
      {(snapshot.error||snapshot.health?.status==='FAILED')&&<p className="failed-run">อ่านหรืออัปเดตรอบล่าสุดไม่สำเร็จ กำลังแสดงชุดที่สำเร็จก่อนหน้า</p>}
      <p className="dam-note">ระดับน้ำเป็นจุดสถานี ไม่ใช่ค่าของทั้งอำเภอ ชุดนี้ไม่รวมข้อมูลฝน เกณฑ์เตือนภัย และการคาดการณ์น้ำท่วม</p>
    </>}
    <a className="source-link" href="https://www.thaiwater.net/" target="_blank" rel="noreferrer">ThaiWater และหน่วยงานผู้วัด <ArrowUpRight size={12}/></a>
  </section>;
}
