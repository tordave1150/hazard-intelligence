'use client';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {useEffect,useMemo,useState} from 'react';
import {Activity,ArrowDownToLine,ArrowLeft,ArrowUpRight,Check,ChevronDown,ChevronRight,CloudRain,Compass,Database,Layers3,MapPin,Mountain,Radio,Search,ShieldCheck,SlidersHorizontal,Waves,X,Satellite,Droplets,Info,RefreshCw,Clock3} from 'lucide-react';
import registry from '@/data/source-registry.json';
import {ageLabel,bangkokTime,contains,freshness,metricColor,metricLabel,metricUnit,metricValue} from '@/lib/semantics';
import type {Area,Forecast,Metric,Snapshot,Source} from '@/lib/types';
const MapView=dynamic(()=>import('./map/map-view'),{ssr:false,loading:()=> <div className="map-loading"><Compass size={28}/><span>Preparing Thailand map…</span></div>});
const empty:Snapshot={records:[],status:null,storage:'unconfigured',error:null,freshness:'UNKNOWN'};

export default function Dashboard({areas}:{areas:Area[]}){
  const lookup=useMemo(()=>new Map(areas.map(a=>[a.id,a])),[areas]);
  const [selected,setSelected]=useState('TH'),[search,setSearch]=useState(''),[snapshot,setSnapshot]=useState<Snapshot>(empty),[loading,setLoading]=useState(true);
  const [metric,setMetric]=useState<Metric>('rainfall_mm'),[date,setDate]=useState(''),[rainfall,setRainfall]=useState(true),[is3d,setIs3d]=useState(false),[terrain,setTerrain]=useState(true),[extrude,setExtrude]=useState(false),[opacity,setOpacity]=useState(74);
  const [sourcesOpen,setSourcesOpen]=useState(false),[leftOpen,setLeftOpen]=useState(false),[rightOpen,setRightOpen]=useState(false),[refresh,setRefresh]=useState(0),[clock,setClock]=useState(Date.now());
  useEffect(()=>{
    if(!sourcesOpen)return;
    const previous=document.activeElement;
    const handle=(event:KeyboardEvent)=>{
      if(event.key==='Escape')setSourcesOpen(false);
      if(event.key==='Tab'){
        const focusable=Array.from(document.querySelectorAll<HTMLElement>('.sources-modal button, .sources-modal a'));
        const first=focusable[0],last=focusable[focusable.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
      }
    };
    document.addEventListener('keydown',handle);
    return()=>{document.removeEventListener('keydown',handle);if(previous instanceof HTMLElement)previous.focus();};
  },[sourcesOpen]);
  const area=lookup.get(selected)??lookup.get('TH')!;
  useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),60000);return()=>clearInterval(timer);},[]);
  useEffect(()=>{
    let active=true;setLoading(true);
    fetch('/api/overview',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(value=>{
      if(!active)return;setSnapshot(value);setDate(current=>value.available_dates.includes(current)?current:(value.available_dates[0]??''));
    }).catch(()=>{if(active)setSnapshot({...empty,error:'Weather snapshot is temporarily unavailable',freshness:'UNAVAILABLE'});}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[refresh]);
  const status=freshness(snapshot.records,clock),stale=status==='STALE'||status==='UNKNOWN'||status==='UNAVAILABLE';
  const recordsById=useMemo(()=>new Map(snapshot.records.map(r=>[r.location_id,r])),[snapshot.records]);
  const current=recordsById.get(area.id);
  const scope=useMemo(()=>snapshot.records.filter(r=>{const a=lookup.get(r.location_id);return a&&contains(area,a);}),[snapshot.records,area,lookup]);
  const dates=[...new Set(snapshot.records.flatMap(r=>r.valid_periods.map(p=>p.date)))].sort();
  const results=search.trim()?areas.filter(a=>a.level!=='national'&&`${a.name} ${a.name_th} ${a.id}`.toLowerCase().includes(search.toLowerCase())).slice(0,8):[];
  const children=areas.filter(a=>a.parent_id===area.id).sort((a,b)=>a.name.localeCompare(b.name));
  const trail:Area[]=[];let parent:Area|undefined=area;while(parent){trail.unshift(parent);parent=parent.parent_id?lookup.get(parent.parent_id):undefined;}
  const select=(id:string)=>{if(!lookup.has(id))return;setSelected(id);setSearch('');setLeftOpen(false);setRightOpen(true);};
  const rainfallValues=scope.map(r=>metricValue(r,date,'rainfall_mm')).filter((v):v is number=>v!==null);
  const max=rainfallValues.length?Math.max(...rainfallValues):null;
  const currentPeriod=current?.valid_periods.find(p=>p.date===date);
  const oldestFetch=snapshot.records.length?snapshot.records.map(r=>r.fetched_at).sort()[0]:null;
  const firstValid=snapshot.records[0]?.valid_periods[0]?.valid_start;
  function download(){
    const blob=new Blob([JSON.stringify({area:area.id,date,source:'Open-Meteo',records:scope},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`thailand-weather-${area.id}-${date||'unavailable'}.json`;a.click();URL.revokeObjectURL(url);
  }
  return <main className="dashboard">
    <a href="#area-navigation" className="skip-link">Skip map to area navigation</a>
    <header className="topbar"><a className="brand" href="/" aria-label="Thailand Hazard Intelligence home"><span className="brand-mark"><Layers3 size={24}/></span><span><b>THAILAND <em>HAZARD INTELLIGENCE</em></b><small>UNIFIED WEATHER & WATER MONITORING</small></span></a>
      <div className="search-wrap"><Search size={17}/><input aria-label="Search area" placeholder="Search province, district, or Thai name…" value={search} onChange={e=>setSearch(e.target.value)}/><kbd>⌕</kbd>
        {search&&<div className="search-results">{results.length?results.map(a=><button key={a.id} onClick={()=>select(a.id)}><MapPin size={14}/><span>{a.name}<small>{a.name_th} · {a.level}</small></span><ChevronRight size={14}/></button>):<p>No matching areas</p>}</div>}
      </div>
      <button className="source-top" onClick={()=>setSourcesOpen(true)}><span className={`status-dot ${status.toLowerCase()}`}/><span>Source status<small>{snapshot.records.length?'1 available · 4 planned':'Awaiting weather snapshot'}</small></span><ChevronDown size={14}/></button>
    </header>
    <div className="situation-title"><div><p className="eyebrow">SITUATION OVERVIEW</p><h1>From national outlook to local understanding.</h1></div><span className="monitoring-badge"><ShieldCheck size={14}/> Monitoring · source-specific evidence</span></div>
    <section className="summary-grid" aria-label="Situation overview">
      <div className="summary-card"><span className="summary-icon teal"><CloudRain size={21}/></span><div><label>Forecast rainfall</label><strong>{max===null?'—':max.toFixed(1)}<small>{max===null?'No data':'mm / 24h'}</small></strong><p>{max===null?'Waiting for a validated snapshot':`Maximum point forecast · ${area.level==='national'?'Thailand':area.name}`}</p></div><span className="mini-tag">FORECAST</span></div>
      <div className="summary-card"><span className="summary-icon blue"><Waves size={21}/></span><div><label>River & rain gauges</label><strong>—<small>Unavailable</small></strong><p>HII / ThaiWater · access pending</p></div></div>
      <div className="summary-card"><span className="summary-icon violet"><Droplets size={21}/></span><div><label>Reservoir status</label><strong>—<small>Unavailable</small></strong><p>RID · source acceptance pending</p></div></div>
      <div className="summary-card"><span className="summary-icon sand"><Satellite size={21}/></span><div><label>Satellite observations</label><strong>—<small>Not connected</small></strong><p>GISTDA · acquisition-dated products</p></div></div>
    </section>
    <section className="map-workspace">
      <div className="workspace-bar"><nav aria-label="Geography breadcrumb">{trail.map((a,i)=><span key={a.id}>{i>0&&<ChevronRight size={12}/>}<button onClick={()=>select(a.id)} aria-current={i===trail.length-1?'location':undefined}>{a.level==='national'?<><Compass size={14}/> Thailand</>:a.name}</button></span>)}</nav><div className="view-controls"><button className="mobile-control" onClick={()=>setLeftOpen(!leftOpen)}><SlidersHorizontal size={15}/> Layers</button><button className={is3d?'':'active'} aria-pressed={!is3d} onClick={()=>setIs3d(false)}>2D</button><button className={is3d?'active':''} aria-pressed={is3d} onClick={()=>setIs3d(true)}>3D</button><button className="mobile-control" onClick={()=>setRightOpen(!rightOpen)}><Info size={15}/> Area</button></div></div>
      <div className="workspace-body">
        <aside className={`left-panel ${leftOpen?'mobile-open':''}`} aria-label="Layers and geography"><div className="panel-heading"><h2><Layers3 size={16}/> Map layers</h2><button className="mobile-close" aria-label="Close layers" onClick={()=>setLeftOpen(false)}><X size={16}/></button></div>
          <p className="panel-description">One map. Independent sources.</p>
          <label className="layer enabled"><CloudRain size={17}/><span><b>Weather forecast</b><small>Open-Meteo</small></span><input type="checkbox" checked={rainfall} onChange={e=>setRainfall(e.target.checked)}/></label>
          <div className="metric-controls"><label htmlFor="metric">Display metric</label><select id="metric" value={metric} onChange={e=>setMetric(e.target.value as Metric)}><option value="rainfall_mm">Rainfall · mm / 24h</option><option value="rain_probability_pct">Chance of rain · %</option></select><label className="opacity-label">Layer opacity <span>{opacity}%</span><input aria-label="Layer opacity" type="range" min="15" max="100" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label></div>
          {[{icon:Radio,name:'Agency warnings',source:'TMD'},{icon:Waves,name:'River & rain gauges',source:'HII / ThaiWater'},{icon:Droplets,name:'Reservoirs & dams',source:'RID'},{icon:Satellite,name:'Flood observations',source:'GISTDA · satellite'}].map(({icon:Icon,name,source})=><label className="layer planned" key={name} title="Disabled until endpoint, permission and data quality are verified"><Icon size={17}/><span><b>{name}</b><small>{source}</small></span><span className="planned-label">Planned</span><input aria-label={name} type="checkbox" disabled hidden/></label>)}
          <div className="terrain-controls"><label className="check-line"><Mountain size={16}/><span>Terrain in 3D</span><input type="checkbox" checked={terrain} onChange={e=>setTerrain(e.target.checked)}/></label><label className="check-line"><Layers3 size={16}/><span>Metric extrusion</span><input type="checkbox" checked={extrude} disabled={!['province','district'].includes(area.level)} onChange={e=>setExtrude(e.target.checked)}/></label><p>Extrusion height scales the selected forecast metric. It does not represent water depth.</p></div>
          <div className="geography-section" id="area-navigation"><h2><MapPin size={16}/> Explore geography</h2><div className="geo-mode"><button className="active">Administrative</button><button disabled title="Authoritative basin geometry pending">Basin <small>Planned</small></button></div>
            {area.level!=='national'&&<button className="back-national" onClick={()=>select('TH')}><ArrowLeft size={13}/> Back to Thailand</button>}
            <p className="list-label">{area.level==='national'?'REGIONS · 6-REGION CLASSIFICATION':area.level==='region'?'PROVINCES':area.level==='province'?'DISTRICTS':'SELECTED DISTRICT'}</p>
            <div className="area-list">{children.length?children.map(a=><button key={a.id} onClick={()=>select(a.id)}><span>{a.name}<small>{a.name_th}</small></span><ChevronRight size={14}/></button>):<div className="selected-district"><Check size={15}/>{area.name}<small>{area.id}</small></div>}</div>
          </div>
          <div className="left-footer"><a href="/methodology"><Info size={13}/> Data & methodology <ArrowUpRight size={12}/></a></div>
        </aside>
        <div className="map-column"><MapView area={area} areas={areas} records={snapshot.records} date={date} metric={metric} is3d={is3d} terrain={terrain} rainfall={rainfall} extrude={extrude} opacity={opacity} stale={stale} onSelect={select}/>
          <div className="legend"><div><b>{metricLabel(metric)}</b><span>{metricUnit(metric)} · representative point</span></div><div className="legend-scale">{(metric==='rainfall_mm'?[0,1,10,25,50]:[0,20,40,60,80]).map(v=><span key={v}><i style={{background:`rgba(${metricColor(v,metric).slice(0,3).join(',')},1)`}}/>{v}{v===(metric==='rainfall_mm'?50:80)?'+':''}</span>)}<span><i className="no-data"/>No data / stale</span></div></div>
        </div>
        <aside className={`right-panel ${rightOpen?'mobile-open':''}`} aria-label="Area intelligence"><div className="panel-heading"><h2>Area intelligence</h2><button className="mobile-close" aria-label="Close area intelligence" onClick={()=>setRightOpen(false)}><X size={16}/></button></div>
          {area.level==='national'?<div className="area-empty"><span className="empty-icon"><MapPin size={26}/></span><h3>A closer look, in context.</h3><p>Select a region, province or district to bring its weather and water evidence together.</p><div className="journey">Thailand <ChevronRight size={12}/> Region <ChevronRight size={12}/> Local</div></div>:<>
          <div className="selected-area"><span className="eyebrow">{area.level.toUpperCase()}</span><h3>{area.name}</h3><p>{area.name_th} <span>{area.id}</span></p></div>
          <div className="evidence-card"><div className="evidence-heading"><CloudRain size={16}/><b>Weather outlook</b><span className="mini-tag">FORECAST</span></div>
            {current?<><div className="area-value">{currentPeriod?.rainfall_mm==null?'—':currentPeriod.rainfall_mm.toFixed(1)}<span>mm / 24h</span></div><p className="value-caption">Forecast rainfall · {date}</p><div className="weather-pair"><span>Chance of rain<b>{currentPeriod?.rain_probability_pct==null?'No data':`${currentPeriod.rain_probability_pct}%`}</b></span><span>Temperature<b>{currentPeriod?.temp_min_c==null||currentPeriod?.temp_max_c==null?'No data':`${currentPeriod.temp_min_c}–${currentPeriod.temp_max_c}°C`}</b></span></div>
            <div className="mini-chart" aria-label="Daily forecast rainfall">{current.valid_periods.map(p=><button className={p.date===date?'active':''} key={p.date} onClick={()=>setDate(p.date)}><span>{p.rainfall_mm??'—'}</span><i style={{height:p.rainfall_mm==null?2:Math.max(3,Math.min(50,p.rainfall_mm*1.2))}}/><small>{new Date(p.date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</small></button>)}</div>
            <p className="coverage-note"><Info size={12}/>{current.spatial_method}. Requested {current.point.lat.toFixed(3)}°N, {current.point.lon.toFixed(3)}°E. Returned grid {current.model_point.lat.toFixed(3)}°N, {current.model_point.lon.toFixed(3)}°E.</p><dl className="time-details"><dt>Valid window</dt><dd>{bangkokTime(currentPeriod?.valid_start)} – {bangkokTime(currentPeriod?.valid_end)}</dd><dt>Model issue time</dt><dd>Not supplied by provider</dd><dt>Retrieved</dt><dd>{bangkokTime(current.fetched_at)}</dd><dt>Quality</dt><dd>{current.quality_status}</dd></dl></>:
            <div className="region-outlook"><strong>{scope.length}</strong><p>{scope.length?'forecast points in this region. Select a province for its point forecast.':'No forecast available for this area.'}</p></div>}
            <a className="source-link" href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather data by Open-Meteo <ArrowUpRight size={12}/></a></div>
          {[{icon:Waves,title:'Water & reservoirs',text:'No connected gauge or dam source.'},{icon:Satellite,title:'Satellite flood observations',text:'No licensed product connected. Acquisition date will be shown.'},{icon:Radio,title:'Official agency warnings',text:'Unavailable. No warning status can be inferred.'}].map(({icon:Icon,title,text})=><div className="unavailable-evidence" key={title}><Icon size={16}/><div><b>{title}</b><p>{text}</p></div><span>—</span></div>)}
          <button className="export-button" disabled={!scope.length} onClick={download}><ArrowDownToLine size={14}/> Export this area’s weather</button></>}
          <div className="freshness-card"><div><Clock3 size={15}/><b>Data freshness</b><span className={`freshness ${status.toLowerCase()}`}>{loading?'LOADING':status}</span></div><p>{snapshot.records.length?`${snapshot.records.length} of 1,005 forecast points available`:'No published weather data'}</p><small>Oldest retrieval: {bangkokTime(oldestFetch)}</small><small>First valid window: {bangkokTime(firstValid)}</small>{snapshot.status?.status==='FAILED'&&<p className="failed-run">Latest ingestion failed · showing last good data</p>}<button onClick={()=>setSourcesOpen(true)}>View all sources <ArrowUpRight size={12}/></button></div>
        </aside>
      </div>
      <footer className="timeline"><div className="timeline-label"><Clock3 size={16}/><span><b>Forecast timeline</b><small>Daily windows · Asia/Bangkok</small></span></div><div className="timeline-dates">{dates.length?dates.map(d=><button className={d===date?'active':''} key={d} onClick={()=>setDate(d)}><span>{new Date(d+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',weekday:'short'})}</span><b>{new Date(d+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</b><i/></button>):<p>{loading?'Loading available forecast windows…':'No forecast windows available'}</p>}</div><button className="refresh-button" disabled={loading} onClick={()=>setRefresh(x=>x+1)}><RefreshCw size={14} className={loading?'spin':''}/><span>Reload snapshot</span></button></footer>
    </section>
    <div className="bottomline"><span><span className={`status-dot ${status.toLowerCase()}`}/>{snapshot.storage==='local'?'Local preview · real API snapshot':snapshot.storage==='mongo'?'Latest published snapshot':'Data connection pending'}{snapshot.error?` · ${snapshot.error}`:''}</span><span>Situation awareness · consult official agency guidance <Link href="/methodology">Methodology <ArrowUpRight size={11}/></Link></span></div>
    {sourcesOpen&&<div className="modal-backdrop" onClick={()=>setSourcesOpen(false)}><section className="sources-modal" role="dialog" aria-modal="true" aria-label="Source status" onClick={e=>e.stopPropagation()}><div className="modal-heading"><div><p className="eyebrow">PROVENANCE & AVAILABILITY</p><h2>Independent sources. Clear timestamps.</h2></div><button autoFocus aria-label="Close source status" onClick={()=>setSourcesOpen(false)}><X size={20}/></button></div><p className="modal-intro">Missing data is unavailable, never an indication of normal or safe conditions. Sources update independently.</p>{(registry as Source[]).map(source=><article className="source-row" key={source.id}><div><h3>{source.organization}<span className="mini-tag">{source.state.replaceAll('_',' ')}</span></h3><p>{source.name} · {source.id==='open_meteo'?(snapshot.records.length?`${status} · ${snapshot.records.length} points`: 'UNAVAILABLE'):source.status}</p><small>{source.description}</small><div className="source-meta"><span>{source.cadence}</span><span>{source.id==='open_meteo'?`Retrieved ${bangkokTime(oldestFetch)}`:'Acceptance pending'}</span></div><a href={source.url} target="_blank" rel="noreferrer">Source documentation <ArrowUpRight size={12}/></a></div></article>)}<Link className="registry-link" href="/sources">Full source registry & terms <ArrowUpRight size={14}/></Link></section></div>}
  </main>;
}
