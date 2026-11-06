'use client';
import type {ReactNode} from 'react';
import {ArrowLeft,ArrowUpRight,Check,ChevronRight,Info,Layers3,MapPin,Mountain,SlidersHorizontal,X} from 'lucide-react';
import type {Area} from '@/lib/types';
import styles from './workspace.module.css';
export type LayerOption={id:string;label:string;detail:string;checked:boolean;disabled:boolean;icon:ReactNode;onChange:(value:boolean)=>void};
type Props={open:boolean;tab:'layers'|'geography';onTab:(tab:'layers'|'geography')=>void;onClose:()=>void;layers:LayerOption[];forecastVisible:boolean;opacity:number;onOpacity:(value:number)=>void;
  terrain:boolean;onTerrain:(value:boolean)=>void;extrude:boolean;onExtrude:(value:boolean)=>void;canExtrude:boolean;area:Area;children:Area[];geography:'administrative'|'basin';onGeography:(value:'administrative'|'basin')=>void;onArea:(id:string)=>void};
export default function LayerControls(p:Props){
  return <aside className={`left-panel ${styles.controls} ${p.open?'mobile-open':styles.closed}`} aria-label="Layers and geography" aria-hidden={!p.open} inert={!p.open}>
    <div className="panel-heading"><h2>{p.tab==='layers'?<><Layers3 size={16}/>Map layers</>:<><MapPin size={16}/>Geography</>}</h2><button aria-label="Close layers" onClick={p.onClose}><X size={18}/></button></div>
    <nav className={styles.leftTabs} aria-label="Control panel"><button aria-pressed={p.tab==='layers'} onClick={()=>p.onTab('layers')}>Layers</button><button aria-pressed={p.tab==='geography'} onClick={()=>p.onTab('geography')}>Geography</button></nav>
    {p.tab==='layers'?<>
      <p className="panel-description">Independent observation overlays. Background and forecast time are in the time dock.</p>
      <fieldset className="source-overlays"><legend>Source overlays</legend>{p.layers.map(l=><label key={l.id} className={`layer ${l.disabled?'planned':'enabled'}`}>{l.icon}<span><b>{l.label}</b><small>{l.detail}</small></span><input aria-label={l.id} type="checkbox" checked={l.checked} disabled={l.disabled} onChange={e=>l.onChange(e.target.checked)}/></label>)}</fieldset>
      <div className="terrain-controls"><h3 className={styles.sectionLabel}><SlidersHorizontal size={14}/> Map preferences</h3>
        {p.forecastVisible&&<label className="opacity-label">Forecast opacity <span>{p.opacity}%</span><input aria-label="Layer opacity" type="range" min="15" max="100" value={p.opacity} onChange={e=>p.onOpacity(+e.target.value)}/></label>}
        <label className="check-line"><Mountain size={16}/><span>Terrain in 3D</span><input type="checkbox" checked={p.terrain} onChange={e=>p.onTerrain(e.target.checked)}/></label>
        <label className="check-line"><Layers3 size={16}/><span>Metric extrusion</span><input type="checkbox" checked={p.extrude} disabled={!p.canExtrude} onChange={e=>p.onExtrude(e.target.checked)}/></label><p>Extrusion scales the forecast metric. It does not represent water depth.</p>
      </div>
    </>:<div className="geography-section" id="area-navigation"><div className="geo-mode"><button className={p.geography==='administrative'?'active':''} onClick={()=>p.onGeography('administrative')}>Administrative</button><button className={p.geography==='basin'?'active':''} onClick={()=>p.onGeography('basin')}>Basin · 22</button></div>
      {p.area.level!=='national'&&<button className="back-national" onClick={()=>p.onArea('TH')}><ArrowLeft size={13}/> Back to Thailand</button>}
      <p className="list-label">{p.geography==='basin'?'22 ลุ่มน้ำ · DDPM context':p.area.level==='national'?'REGIONS · 6-REGION CLASSIFICATION':p.area.level==='region'?'PROVINCES':p.area.level==='province'?'DISTRICTS':'SELECTED DISTRICT'}</p>
      <div className="area-list">{p.children.length?p.children.map(a=><button key={a.id} onClick={()=>p.onArea(a.id)}><span>{a.name}<small>{a.name_th}</small></span><ChevronRight size={14}/></button>):<div className="selected-district"><Check size={15}/>{p.area.name}<small>{p.area.id}</small></div>}</div>
    </div>}
    <div className="left-footer"><a href="/health"><Info size={13}/> Data health <ArrowUpRight size={12}/></a><a href="/methodology">Methodology & attribution <ArrowUpRight size={12}/></a></div>
  </aside>;
}
