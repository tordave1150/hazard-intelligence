import Link from 'next/link';
import registry from '@/data/source-registry.json';
export default function Sources(){return <main className="document-page"><Link href="/">← Return to unified map</Link><h1>Source registry</h1><p><Link href="/health">Data health · สุขภาพระบบข้อมูล →</Link></p><p>Integration status records acceptance progress. Runtime data freshness appears in the map’s Source status panel. A planned source has no active layer.</p>
  <section id="precipitation-review" aria-labelledby="precipitation-review-heading">
    <h2 id="precipitation-review-heading">Nowcasting / QPE · แหล่งที่กำลังตรวจรับ</h2>
    <p>ตรวจล่าสุด 5 พฤศจิกายน 2026 เวลา 20:56 ICT · ยังไม่มีเลเยอร์พยากรณ์ฝนระยะสั้นหรือ QPE เชิงตัวเลขจากแหล่งด้านล่าง การตรวจนี้แยกจากภาพเรดาร์สังเกตการณ์ที่เปิดดูบนแผนที่ได้แล้ว</p>
    <article><h3>TMD / SATDA · Nowcasting ภาคใต้</h3>
      <p>พบชุดภาพสังเกตการณ์และภาพพยากรณ์ระดับภูมิภาค แต่ยังต้องยืนยันเวลาออกพยากรณ์ ช่วงคาดการณ์ พื้นที่ที่มีข้อมูลใช้ได้ และเงื่อนไขการนำภาพมาแสดงซ้ำ ก่อนเปิดใช้งานในแผนที่</p>
      <p><a href="https://satda.tmd.go.th/wp-content/uploads/data/dashboard/radar_map/south_nowcast.php">ดู Nowcasting ที่เว็บไซต์ทางการ →</a></p>
    </article>
    <article><h3>TMD · ข้อมูลฝนเชิงตัวเลข</h3>
      <p>ไฟล์ต้นทางยังไม่ระบุหน่วยและความหมายของค่าฝนเพียงพอที่จะยืนยันว่าเป็นอัตราฝนหรือฝนสะสม ต้องตรวจตำแหน่งช่องข้อมูลและความหมายของพื้นที่ไม่มีข้อมูลด้วย จึงยังไม่ใช้คำนวณปริมาณฝนรายพื้นที่</p>
      <p><a href="https://weather.tmd.go.th/composite/index_composite.html">ดูข้อมูลเรดาร์ที่เว็บไซต์ทางการ →</a></p>
    </article>
    <p>ตัวอย่าง Nowcasting กรุงเทพฯ และขอนแก่นที่ตรวจพบยังเป็นข้อมูลเก่า จึงยังไม่ใช้เป็นข้อมูลล่าสุด แหล่งระดับภูมิภาคสามารถเพิ่มได้เมื่อผ่านการตรวจรับ โดยระบุพื้นที่รองรับตามจริง</p>
  </section>
  {registry.map(s=><article key={s.id}><h2>{s.organization} · {s.name}</h2><p>{s.description}</p><dl>{Object.entries(s).filter(([key])=>!['description','name','organization'].includes(key)).map(([k,v])=><div key={k} style={{display:'contents'}}><dt>{k.replaceAll('_',' ')}</dt><dd>{k.endsWith('url')?<a href={v!}>{v}</a>:v??'Unverified / not connected'}</dd></div>)}</dl></article>)}</main>;}
