'use client';
import {Info,Layers3,MapPin} from 'lucide-react';
import styles from './workspace.module.css';
export default function WorkspaceRail({leftOpen,tab,inspectorOpen,onPanel,onInspector}:{leftOpen:boolean;tab:'layers'|'geography';inspectorOpen:boolean;onPanel:(tab:'layers'|'geography')=>void;onInspector:()=>void}){
  return <nav className={styles.rail} aria-label="Map workspace tools">
    <button title="Layers" aria-label="Open layers" aria-pressed={leftOpen&&tab==='layers'} onClick={()=>onPanel('layers')}><Layers3 size={20}/><span>Layers</span></button>
    <button title="Geography" aria-label="Open geography" aria-pressed={leftOpen&&tab==='geography'} onClick={()=>onPanel('geography')}><MapPin size={20}/><span>Explore</span></button>
    <button title="Inspector" aria-label="Toggle inspector" aria-pressed={inspectorOpen} onClick={onInspector}><Info size={20}/><span>Inspect</span></button>
    <span className={styles.railFoot}>TH</span>
  </nav>;
}
