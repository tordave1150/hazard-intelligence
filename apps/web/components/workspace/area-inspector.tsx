'use client';
import {ArrowUpRight,MapPin} from 'lucide-react';
import type {Area} from '@/lib/types';
import type {InspectorId} from '@/lib/workspace';
import styles from './workspace.module.css';
export type SourceShortcut={id:InspectorId;title:string;detail:string;disabled?:boolean};
export default function AreaInspector({area,sources,onSource}:{area:Area;sources:SourceShortcut[];onSource:(id:InspectorId)=>void}){
  return <section className={styles.areaOverview} aria-label="Selected area overview"><span className={styles.sectionLabel}><MapPin size={15}/>{area.level}</span><h3>{area.name}</h3><p>{area.name_th} <small>{area.id}</small></p>
    <p className={styles.guidance}>เลือกจุดบนแผนที่หรือแหล่งข้อมูลเพื่อดูรายละเอียด · แต่ละแหล่งใช้เวลาและขอบเขตของตนเอง</p>
    <div className={styles.sourceShortcuts}>{sources.map(s=><button key={s.id} disabled={s.disabled} onClick={()=>onSource(s.id)}><span><b>{s.title}</b><small>{s.detail}</small></span><ArrowUpRight size={14}/></button>)}</div>
    <p className={styles.guidance}>Missing or empty data does not establish safe conditions. Station observations are points; province references do not establish district-wide conditions.</p>
  </section>;
}
