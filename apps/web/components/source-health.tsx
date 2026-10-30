'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {Activity,ArrowUpRight,CheckCircle2,Clock3,RefreshCw} from 'lucide-react';
import {bangkokTime} from '@/lib/semantics';
import {healthError,type RuntimeSource} from '@/lib/source-health';

type Result={checked_at:string;sources:RuntimeSource[]};
const names={OK:'ปกติ',ATTENTION:'ควรตรวจสอบ',FAILED:'รอบล่าสุดล้มเหลว',OVERDUE:'เลยช่วงอัปเดต',RUNNING:'กำลังอัปเดต',STALLED:'รันนานกว่าปกติ',UNKNOWN:'ยังยืนยันไม่ได้',PLANNED:'ยังไม่เชื่อมต่อ'};
const time=(value:unknown)=>bangkokTime(typeof value==='string'?value:null);
export default function SourceHealth(){
  const [data,setData]=useState<Result|null>(null),[error,setError]=useState(false),[busy,setBusy]=useState(true),[refresh,setRefresh]=useState(0);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const load=async()=>{
      setBusy(true);
      try{
        const response=await fetch('/api/sources/status',{cache:'no-store',signal:controller.signal});
        if(!response.ok)throw Error();
        const value=await response.json() as Result;
        if(!Array.isArray(value.sources)||value.sources.some(s=>!s.monitoring))throw Error();
        if(active){setData(value);setError(false);}
      }catch{if(active)setError(true);}finally{if(active)setBusy(false);}
    };
    void load();const timer=setInterval(load,60000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh]);
  const attention=data?.sources.filter(s=>s.monitoring.needs_attention).length??0;
  const connected=data?.sources.filter(s=>s.monitoring.state!=='PLANNED').length??0;
  return <main className="health-page">
    <nav><Link href="/">← กลับแผนที่</Link><Link href="/sources">แหล่งข้อมูลและเงื่อนไข <ArrowUpRight size={13}/></Link></nav>
    <header><div><p className="eyebrow">DATA HEALTH</p><h1><Activity size={26}/> สุขภาพระบบข้อมูล</h1><p>ตรวจการดึงข้อมูล ความสด และปัญหาที่ต้นทางแยกกัน · เวลาไทย (ICT)</p></div>
      <button className="health-refresh" disabled={busy} onClick={()=>setRefresh(x=>x+1)}><RefreshCw size={16} className={busy?'spin':''}/>{busy?'กำลังตรวจ…':'ตรวจสถานะอีกครั้ง'}</button></header>
    <section className="health-overview" aria-label="สรุปสุขภาพข้อมูล"><div><CheckCircle2 size={19}/><strong>{data?connected:'—'}</strong><span>แหล่งที่ติดตาม</span></div><div><Activity size={19}/><strong>{data?attention:'—'}</strong><span>แหล่งที่ควรตรวจสอบ</span></div><div><Clock3 size={19}/><span>ตรวจหน้าเว็บล่าสุด<br/><b>{time(data?.checked_at)}</b></span></div></section>
    {error&&<p className="health-error" role="alert">ตรวจสถานะรอบนี้ไม่สำเร็จ {data?'กำลังแสดงผลตรวจครั้งก่อนตามเวลาข้างต้น':'ลองตรวจอีกครั้ง'}</p>}
    <p className="health-explainer">หน้านี้อ่านสถานะที่บันทึกไว้ทุก 60 วินาที ปุ่มตรวจสถานะไม่ได้สั่งดึงข้อมูลจากหน่วยงานใหม่ ตาราง GitHub Actions เป็นรอบเป้าหมายและอาจล่าช้าได้</p>
    {!data&&!error&&<p role="status">กำลังอ่านสถานะของแต่ละแหล่งข้อมูล…</p>}
    <section className="health-grid" aria-label="สถานะแต่ละแหล่งข้อมูล">{data?.sources.map(source=>{
      const m=source.monitoring,h=source.health,reason=healthError(h);
      return <article className="health-card" key={source.id}><div className="health-card-heading"><div><small>{source.organization}</small><h2>{source.name}</h2></div><span className={`health-badge health-${m.state.toLowerCase()}`}>{names[m.state]}</span></div>
        <p className="health-reason">{m.reason}</p>
        {m.state!=='PLANNED'&&<dl><dt>รอบล่าสุด</dt><dd>{String(h?.status??'ไม่พบสถานะ')}{m.run_url&&<> · <a href={m.run_url} target="_blank" rel="noreferrer">เปิดรัน <ArrowUpRight size={11}/></a></>}</dd>
          <dt>เริ่มดึงล่าสุด</dt><dd>{time(h?.last_attempt)}</dd><dt>สำเร็จล่าสุด</dt><dd>{time(h?.last_success)}</dd>
          <dt>ความสด{['gistda','thaiwater','thaiwater_rain'].includes(source.id)?'ของการดึง':''}</dt><dd>{source.query_freshness??source.freshness}{source.id==='gistda'&&' · เวลาถ่ายภาพไม่ทราบ'}{source.id.startsWith('thaiwater')&&' · เวลาตรวจวัดไม่ระบุเขตเวลา'}</dd>
          <dt>รอบเป้าหมาย</dt><dd>ทุก {m.cadence_hours} ชั่วโมง</dd><dt>ควรพบรอบใหม่ภายใน</dt><dd>{time(m.expected_by)}{m.overdue?' · เลยช่วงแล้ว':''}</dd>
          <dt>จำนวนในชุดล่าสุด</dt><dd>{typeof h?.record_count==='number'?h.record_count.toLocaleString('en-US'):typeof h?.successful_locations==='number'?h.successful_locations.toLocaleString('en-US'):'ไม่ระบุ'}</dd>
          {!!m.quality_issue_count&&<><dt>ปัญหาคุณภาพต้นทาง</dt><dd>{m.quality_issue_count} รายการ · เก็บข้อมูลเดิมพร้อมป้ายกำกับ</dd></>}
          {source.id.startsWith('thaiwater')&&typeof h?.time_unknown_count==='number'&&<><dt>อายุการตรวจวัดยังไม่ยืนยัน</dt><dd>{h.time_unknown_count} สถานี · แยกจากปัญหาคุณภาพรายการ</dd></>}
        </dl>}
        {reason&&<p className="health-error-detail">{reason}{typeof h?.http_status==='number'?` (HTTP ${h.http_status})`:''}</p>}
        <div className="health-card-links">{m.actions_url&&<a href={m.actions_url} target="_blank" rel="noreferrer">ประวัติ GitHub Actions <ArrowUpRight size={13}/></a>}<a href={source.url} target="_blank" rel="noreferrer">ต้นทาง <ArrowUpRight size={13}/></a></div>
      </article>;
    })}</section>
    <p className="health-explainer">ความสำเร็จของการดึงข้อมูลไม่ได้ยืนยันว่าไม่มีภัยพิบัติ ข้อมูลที่ขาดหายไม่หมายถึงพื้นที่ปลอดภัย รายละเอียดความหมายและข้อจำกัดอยู่ใน <Link href="/methodology">Data & methodology</Link></p>
  </main>;
}
