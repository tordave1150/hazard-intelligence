'use client';
import {useEffect,useMemo,useState} from 'react';
import {ArrowUpRight,RefreshCw,Search,X} from 'lucide-react';
import type {ProvinceOverview as Overview} from '@/lib/provinces';
import {areas} from '@/lib/geography';
import {bangkokTime} from '@/lib/semantics';
const labels:Record<string,string>={forecast:'พยากรณ์ฝน',rain:'สถานีฝนตรวจวัด',warnings:'คำเตือน TMD',gauges:'สถานีระดับน้ำ',dams:'เขื่อน RID',satellite:'GISTDA 3 วัน'};
export default function ProvinceOverview({onSelect,onClose}:{onSelect:(id:string)=>void;onClose:()=>void}){
  const [data,setData]=useState<Overview|null>(null),[error,setError]=useState(false),[busy,setBusy]=useState(true),[refresh,setRefresh]=useState(0);
  const [search,setSearch]=useState(''),[region,setRegion]=useState(''),[filter,setFilter]=useState('all'),[sort,setSort]=useState('name');
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const load=async()=>{setBusy(true);try{
      const response=await fetch('/api/provinces/overview',{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error();
      const value=await response.json() as Overview;if(value.rows?.length!==77||new Set(value.rows.map(r=>r.area_id)).size!==77)throw Error();
      if(active){setData(value);setError(false);}
    }catch{if(active)setError(true);}finally{if(active)setBusy(false);}};
    void load();const timer=setInterval(load,300000);return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh]);
  const rows=useMemo(()=>(data?.rows??[]).filter(r=>(!region||r.region_id===region)&&`${r.name} ${r.name_th} ${r.area_id}`.toLowerCase().includes(search.toLowerCase())&&
    (filter==='all'||filter==='warnings'&&(r.warnings?.current??0)>0||filter==='gaps'&&r.data_gaps.length>0))
    .sort((a,b)=>sort==='warnings'?(b.warnings?.current??-1)-(a.warnings?.current??-1)||a.name_th.localeCompare(b.name_th,'th'):
      sort==='rain'?(b.forecast?.rainfall_mm??-1)-(a.forecast?.rainfall_mm??-1)||a.name_th.localeCompare(b.name_th,'th'):a.name_th.localeCompare(b.name_th,'th')),[data,region,search,filter,sort]);
  return <section className="province-overview" aria-label="เปรียบเทียบสถานการณ์ 77 จังหวัด">
    <header><div><p className="eyebrow">NATIONAL PROVINCE COMPARISON</p><h2>สถานการณ์ 77 จังหวัด</h2><p>ข้อมูลสถานการณ์ล่าสุดและพยากรณ์วันนี้ {data?.forecast_date??'…'} · แยกเวลาของแต่ละแหล่ง</p></div>
      <div className="province-actions"><button disabled={busy} onClick={()=>setRefresh(n=>n+1)} aria-label="โหลดสรุปจังหวัดอีกครั้ง"><RefreshCw size={15} className={busy?'spin':''}/></button><button onClick={onClose} aria-label="ปิดสรุปจังหวัด"><X size={18}/></button></div></header>
    <div className="province-filters"><label><Search size={14}/><input aria-label="ค้นหาจังหวัดในสรุป" placeholder="ชื่อจังหวัดหรือรหัส" value={search} onChange={e=>setSearch(e.target.value)}/></label>
      <select aria-label="กรองภาคในสรุป" value={region} onChange={e=>setRegion(e.target.value)}><option value="">ทุกภาค</option>{areas.filter(a=>a.level==='region').map(a=><option key={a.id} value={a.id}>{a.name_th}</option>)}</select>
      <select aria-label="กรองสถานการณ์จังหวัด" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">ทุกจังหวัด</option><option value="warnings">มีคำเตือนที่มีผลตามเวลา</option><option value="gaps">มีข้อมูลขาดหรือรายการต้องตรวจ</option></select>
      <select aria-label="เรียงจังหวัด" value={sort} onChange={e=>setSort(e.target.value)}><option value="name">เรียงชื่อจังหวัด</option><option value="warnings">จำนวนคำเตือน TMD</option><option value="rain">ฝนพยากรณ์ ณ จุดจังหวัด</option></select></div>
    {error&&<p className="province-error" role="alert">อ่านสรุปรอบนี้ไม่สำเร็จ {data?'กำลังแสดงชุดก่อนตามเวลาข้างล่าง':''}</p>}
    {!data&&!error?<p role="status">กำลังอ่านสรุปทั้ง 77 จังหวัด…</p>:data&&<>
      <p className="province-caption">{rows.length} / 77 จังหวัด · ตรวจชุดข้อมูล {bangkokTime(data.checked_at)} · “—” คือยังไม่มีข้อมูล ส่วน 0 คือจำนวนรายการในคำตอบชุดนี้</p>
      <div className="province-table-wrap"><table className="province-table"><thead><tr><th>จังหวัด</th><th>ฝนพยากรณ์<br/>mm / 24h</th><th>คำเตือน TMD<br/>มีผลตามเวลา</th><th>สถานีระดับน้ำ<br/>HII</th><th>สถานีฝน<br/>HII</th><th>เขื่อน<br/>RID</th><th>ผลลัพธ์<br/>GISTDA 3 วัน</th><th>รายละเอียด</th></tr></thead><tbody>{rows.map(r=><tr key={r.area_id}>
        <th scope="row"><button onClick={()=>onSelect(r.area_id)}>{r.name_th}<small>{r.name}</small></button></th>
        <td>{r.forecast?.rainfall_mm===null||!r.forecast?'—':r.forecast.rainfall_mm.toFixed(1)}</td>
        <td>{r.warnings?.current??'—'}{(r.warnings?.time_unknown??0)>0&&<small>เวลาไม่ยืนยัน {r.warnings!.time_unknown}</small>}</td>
        <td>{r.gauges?.count??'—'}{r.gauges&&r.gauges.quality_issues>0&&<small>ตรวจรายการ {r.gauges.quality_issues}</small>}</td>
        <td>{r.rain?.count??'—'}</td><td>{r.dams?.count??'—'}</td><td>{r.flood_features??'—'}</td><td><button className="province-open" onClick={()=>onSelect(r.area_id)} aria-label={`ดูจังหวัด${r.name_th}`}>ดูแผนที่ <ArrowUpRight size={12}/></button>
          {r.data_gaps.length>0&&<small>ตรวจข้อมูล: {r.data_gaps.map(id=>labels[id]).join(', ')}</small>}</td></tr>)}</tbody></table></div>
      {!rows.length&&<p className="province-caption">ไม่พบจังหวัดที่ตรงกับตัวกรอง</p>}
      <details className="province-clocks"><summary>เวลา ขอบเขต และความสดของแต่ละแหล่ง</summary><div>{Object.entries(data.sources).map(([id,s])=><article key={id}><b>{labels[id]} · {s.freshness}</b><p>ดึง {bangkokTime(s.fetched_at)}</p><p>{s.note}</p></article>)}</div></details>
      <p className="province-caption">จำนวนสถานี เขื่อน และผลลัพธ์ดาวเทียมใช้คนละความหมาย การไม่มีรายการไม่ยืนยันว่าปลอดภัย ข้อมูลขาดรวมถึงไม่มีสถานีในคำตอบหรือค่าที่ไม่ผ่านรูปแบบ การเรียงฝนใช้พยากรณ์จุดตัวแทนจังหวัด ไม่ใช่การจัดอันดับความเสี่ยงน้ำท่วม</p>
    </>}
  </section>;
}
