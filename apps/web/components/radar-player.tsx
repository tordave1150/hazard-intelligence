'use client';
import {useEffect,useState} from 'react';
import {Play,Pause,ChevronLeft,ChevronRight} from 'lucide-react';
import {bangkokTime} from '@/lib/semantics';
import {radarFreshness,radarMissingSlots,radarVisible,type RadarLoad,type RadarSnapshot} from '@/lib/radar';

const scale=[['#54A431','0.21'],['#5EB738','0.24'],['#66C43C','0.50'],['#66C43C','0.72'],['#69CB5A','1.03'],['#73DE45','1.47'],['#7BEC4B','2.10'],['#F3F453','3.00'],['#DEDF4B','4.29'],['#D6D648','6.13'],['#F1C946','8.76'],['#D79C37','12.5'],['#D79C37','17.9'],['#E3622A','25.6'],['#D43320','36.5'],['#CA325D','52.2'],['#B72D54','74.6'],['#B72D54','106.7'],['#E345F5','152.5'],['#EA8CF8','217.9'],['#F3CBFA','311.4'],['#EFE6F1','445.0'],['#EFE6F1','>636.0']];
type Props={snapshot:RadarSnapshot;index:number;onIndex:(index:number)=>void;opacity:number;onOpacity:(value:number)=>void;load:RadarLoad|null;now:number};
export default function RadarPlayer({snapshot,index,onIndex,opacity,onOpacity,load,now}:Props){
  const [playing,setPlaying]=useState(false),frames=snapshot.feed?.frames??[],frame=frames[index],freshness=radarFreshness(snapshot.feed,now);
  const visible=radarVisible(freshness),loaded=!!frame&&load?.id===frame.sha256&&load.status==='loaded';
  const failed=!!frame&&load?.id===frame.sha256&&load.status==='error';
  const running=playing&&visible&&!failed;
  useEffect(()=>{
    if(!running||!loaded||!visible||frames.length<2)return;
    const timer=setTimeout(()=>onIndex((index+1)%frames.length),1000);return()=>clearTimeout(timer);
  },[running,loaded,visible,index,frames.length,onIndex]);
  return <section className="radar-player" aria-label="TMD radar player">
    <div className="radar-title"><b>TMD Radar Composite · ความเข้มฝนโดยประมาณ · mm/hour</b><span className="radar-status">{freshness}</span></div>
    <p className="radar-clock" role="status">{frame?<>ภาพที่เลือก: <b>{bangkokTime(frame.observed_at)}</b> · ต้นทาง UTC {frame.observed_at.replace('T',' ').replace('Z','')} · {index+1}/{frames.length}</>:'ยังไม่มีชุดภาพเรดาร์ที่ตรวจสอบแล้ว'}</p>
    <p className="radar-load" role="status">{!visible?'หยุดแสดงภาพ: ข้อมูลเก่าหรือยังยืนยันเวลาไม่ได้':failed?'โหลดภาพไม่สำเร็จ · ยังไม่แสดงภาพ เลือกเวลาอื่นหรือลองใหม่':loaded?(index===frames.length-1?'กำลังแสดงภาพล่าสุดในชุด':'กำลังแสดงภาพย้อนหลัง'):'กำลังโหลด · ยังไม่แสดงภาพที่เลือก'}</p>
    {snapshot.health?.status==='FAILED'&&<p>รอบเก็บล่าสุดไม่สำเร็จ · กำลังใช้ชุดภาพล่าสุดที่ตรวจผ่านตามเวลาที่แสดง</p>}
    <div className="radar-playback"><button aria-label={running?'Pause radar':'Play radar'} disabled={!visible||frames.length<2||failed} onClick={()=>setPlaying(value=>!value)}>{running?<Pause size={15}/>:<Play size={15}/>}</button>
      <button aria-label="Previous radar frame" disabled={!visible||index<=0} onClick={()=>{setPlaying(false);onIndex(index-1);}}><ChevronLeft size={16}/></button>
      <input type="range" aria-label="Radar frame" min={0} max={Math.max(0,frames.length-1)} value={Math.min(index,Math.max(0,frames.length-1))} disabled={!visible||frames.length<2} onChange={e=>{setPlaying(false);onIndex(Number(e.target.value));}}/>
      <button aria-label="Next radar frame" disabled={!visible||index>=frames.length-1} onClick={()=>{setPlaying(false);onIndex(index+1);}}><ChevronRight size={16}/></button>
      <button className="radar-latest" disabled={!visible||index===frames.length-1} onClick={()=>{setPlaying(false);onIndex(frames.length-1);}}>Latest</button>
      <label>Opacity {opacity}%<input aria-label="Radar opacity" type="range" min="20" max="100" value={opacity} onChange={e=>onOpacity(Number(e.target.value))}/></label>
    </div>
    <div className="radar-scale" aria-label="TMD rain rate color scale in millimeters per hour">{scale.map(([color,label],i)=><span key={i} title={label+' mm/hour'} style={{background:color}}/>)}</div>
    <div className="radar-scale-labels"><span>0.21</span><span>2.10</span><span>12.5</span><span>52.2</span><span>217.9</span><span>&gt;636</span></div>
    <p>พื้นที่โปร่งใส/ไม่มีสี: ยังยืนยันไม่ได้ว่าไม่มีฝนหรือเรดาร์ขาดข้อมูล · echo อาจมีสิ่งที่ไม่ใช่ฝน · ขอบภาพไม่รับรองพื้นที่ตรวจวัดครบ</p>
    <details><summary>เวลา แหล่งข้อมูล และระดับสี</summary><p>ล่าสุดในชุด {bangkokTime(frames.at(-1)?.observed_at)} · เก็บข้อมูล {bangkokTime(snapshot.feed?.fetched_at)} · รอบเก็บ {String(snapshot.health?.status??'UNKNOWN')} · เป้าหมายทุก 15 นาที ตารางอาจล่าช้า</p>
      {snapshot.feed&&radarMissingSlots(snapshot.feed)>0&&<p>ขาดช่วงเวลา 15 นาทีภายในชุด {radarMissingSlots(snapshot.feed)} ช่วง · ไม่เติมภาพหรือค่าฝนเอง</p>}
      <p>ค่าประมาณจาก PCAPPI ระดับ 2 km และสมการ Z–R ตาม TMD · ใช้เวลาและสีของแต่ละภาพ แยกจากพยากรณ์และฝนสะสมสถานี</p>
      <ul className="radar-scale-detail">{scale.map(([color,label],i)=><li key={i}><i style={{background:color}}/>{label} mm/hour</li>)}</ul>
    </details>
    <p className="radar-attribution">กรมอุตุนิยมวิทยา (TMD) · <a href="https://weather.tmd.go.th/composite/index_composite.html" target="_blank" rel="noreferrer">ดูต้นทาง</a> · <a href="https://www.tmd.go.th/content/copyright" target="_blank" rel="noreferrer">เงื่อนไขการใช้</a></p>
  </section>;
}
