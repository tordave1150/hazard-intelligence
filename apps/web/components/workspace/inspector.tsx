'use client';
import {useEffect,useRef,type ReactNode,type Ref} from 'react';
import {X} from 'lucide-react';
import {inspectorLabels,type InspectorId} from '@/lib/workspace';
import styles from './workspace.module.css';
export default function ContextInspector({open,context,contexts,onContext,onClose,panelRef,children}:{open:boolean;context:InspectorId;contexts:InspectorId[];onContext:(id:InspectorId)=>void;onClose:()=>void;panelRef:Ref<HTMLElement>;children:ReactNode}){
  const body=useRef<HTMLDivElement>(null);
  useEffect(()=>{body.current?.scrollTo({top:0});},[context]);
  return <aside ref={panelRef} className={`right-panel ${styles.inspector} ${open?'mobile-open':styles.closed}`} aria-label="Area intelligence" aria-hidden={!open} inert={!open}>
    <div className={`panel-heading ${styles.inspectorHeading}`}><div><small>CONTEXT / EVIDENCE</small><h2>{inspectorLabels[context]}</h2></div><button aria-label="Close area intelligence" onClick={onClose}><X size={18}/></button></div>
    <nav className={styles.inspectorTabs} aria-label="Inspector context">{['area',...contexts.filter(id=>id!=='area')].map(id=><button key={id} aria-pressed={context===id} onClick={()=>onContext(id as InspectorId)}>{inspectorLabels[id as InspectorId]}</button>)}</nav>
    <div ref={body} className={styles.inspectorBody} data-inspector-context={context}>{children}</div>
  </aside>;
}
