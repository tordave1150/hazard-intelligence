import {stationColors} from '@/lib/map-stations';

export type MapLegendEntry={kind:'water'|'rain'|'dam'|'warning'|'flood';detail:string};
const labels={water:'ระดับน้ำ (น้ำ)',rain:'ฝนสถานี (ฝน)',dam:'เขื่อน RID',warning:'คำเตือน CAP',flood:'น้ำท่วม GISTDA'};

export default function MapLegend({entries}:{entries:MapLegendEntry[]}){
  const stations=entries.some(entry=>entry.kind==='water'||entry.kind==='rain');
  return <section className="map-evidence" aria-label="Map layer legend">
    <div className="map-key-row"><b>สัญลักษณ์</b><ul className="map-key-items">{entries.map(({kind})=><li key={kind}>
      <i aria-hidden="true" className={`map-key-symbol map-key-${kind}`} style={kind==='water'||kind==='rain'?{background:stationColors[kind]}:undefined}>{kind==='dam'?'◆':null}</i>
      <span>{labels[kind]}</span>
    </li>)}</ul>{entries.length===0&&<span className="map-key-empty">ยังไม่ได้เปิดเลเยอร์ข้อมูลสังเกตการณ์</span>}</div>
    {stations&&<p className="map-key-note">กลุ่ม “น้ำ / ฝน” นับรายการแยกประเภท บางสถานีมีพิกัดเดียวกัน · สีจุดแยกชนิดข้อมูล ไม่ใช่เกณฑ์อันตราย</p>}
    {entries.length>0&&<details className="map-source-notes"><summary>เวลาและความหมายข้อมูล · {entries.length} เลเยอร์</summary>
      <ul>{entries.map(({kind,detail})=><li key={kind}><b>{labels[kind]}</b><span>{detail}</span></li>)}</ul>
    </details>}
  </section>;
}
