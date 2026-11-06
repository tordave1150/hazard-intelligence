'use client';
import {useEffect,useId,useRef,type ReactNode} from 'react';
import {X} from 'lucide-react';
import styles from './workspace.module.css';
export default function WorkspaceDialog({title,onClose,children}:{title:string;onClose:()=>void;children:ReactNode}){
  const panel=useRef<HTMLElement>(null),titleId=useId(),closeRef=useRef(onClose);closeRef.current=onClose;
  useEffect(()=>{
    const opener=document.activeElement as HTMLElement|null,root=panel.current;
    root?.querySelector<HTMLElement>('button')?.focus();
    const onKey=(e:KeyboardEvent)=>{
      if(e.key==='Escape'){e.preventDefault();closeRef.current();return;}
      if(e.key!=='Tab'||!root)return;
      const nodes=[...root.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),[tabindex="0"]')].filter(n=>n.getClientRects().length);
      const first=nodes[0],last=nodes.at(-1);
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
    };
    document.addEventListener('keydown',onKey);
    return()=>{document.removeEventListener('keydown',onKey);if(opener?.isConnected)opener.focus({preventScroll:true});};
  },[]);
  return <div className={styles.dialogBackdrop} onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}><section ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} className={styles.dialog}>
    <header><h2 id={titleId}>{title}</h2><button onClick={onClose} aria-label={`Close ${title}`}><X size={20}/></button></header>{children}
  </section></div>;
}
