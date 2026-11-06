'use client';
import {useId,useMemo,useRef,useState,type MouseEvent} from 'react';
import {Activity,ArrowUpRight,BarChart3,Layers3,MapPin,Search} from 'lucide-react';
import type {Area} from '@/lib/types';
import styles from './workspace.module.css';
type Props={areas:Area[];available:number;total:number;onSelect:(id:string)=>void;onSources:(event:MouseEvent<HTMLButtonElement>)=>void;onSummary:()=>void;onCompare:()=>void};
export default function WorkspaceTopbar({areas,available,total,onSelect,onSources,onSummary,onCompare}:Props){
  const [query,setQuery]=useState(''),[active,setActive]=useState(0),input=useRef<HTMLInputElement>(null),listId=useId();
  const results=useMemo(()=>query.trim()?areas.filter(a=>a.level!=='national'&&`${a.name} ${a.name_th} ${a.id}`.toLowerCase().includes(query.trim().toLowerCase())).slice(0,8):[],[query,areas]);
  const select=(id:string)=>{onSelect(id);setQuery('');setActive(0);input.current?.focus();};
  return <header className={`topbar ${styles.topbar}`}>
    <a className="brand" href="/" aria-label="Thailand Hazard Intelligence home"><span className="brand-mark"><Layers3 size={22}/></span><span><b>THAILAND <em>HAZARD INTELLIGENCE</em></b><small>WEATHER & WATER · SOURCE-SPECIFIC EVIDENCE</small></span></a>
    <div className={`search-wrap ${styles.search}`}><Search size={17}/><input ref={input} aria-label="Search area" role="combobox" aria-expanded={!!query.trim()} aria-controls={listId} aria-autocomplete="list" aria-activedescendant={results[active]?`${listId}-${active}`:undefined} placeholder="Search Thailand · จังหวัด / อำเภอ" value={query}
      onChange={e=>{setQuery(e.target.value);setActive(0);}} onKeyDown={e=>{
        if(e.key==='Escape'){setQuery('');return;}
        if(!results.length)return;
        if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();setActive(i=>(i+(e.key==='ArrowDown'?1:-1)+results.length)%results.length);}
        if(e.key==='Enter'){e.preventDefault();select(results[active].id);}
      }}/><kbd>⌕</kbd>
      {query.trim()&&<div className="search-results" role="listbox" id={listId} aria-label="Area search results">{results.length?results.map((a,i)=><button id={`${listId}-${i}`} key={a.id} type="button" role="option" aria-selected={i===active} tabIndex={-1} onMouseDown={e=>e.preventDefault()} onClick={()=>select(a.id)}><MapPin size={14}/><span>{a.name}<small>{a.name_th} · {a.level}</small></span><ArrowUpRight size={13}/></button>):<p>No matching areas</p>}</div>}
    </div>
    <div className={styles.topActions}><button onClick={onSummary} aria-label="Open situation overview">Overview</button><button onClick={onCompare} aria-label="Compare 77 provinces"><BarChart3 size={16}/><span>77 provinces</span></button>
      <button className="source-top" onClick={onSources} aria-label={`Source status ${available} available of ${total}`}><Activity size={16}/><span>Sources<small>{available}/{total} available · age varies</small></span></button></div>
  </header>;
}
