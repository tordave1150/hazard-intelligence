'use client';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {useEffect,useMemo,useRef,useState} from 'react';
import type {MouseEvent as ReactMouseEvent} from 'react';
import {Activity,ArrowDownToLine,ArrowLeft,ArrowUpRight,Check,ChevronDown,ChevronRight,CloudRain,Compass,Database,Layers3,MapPin,Mountain,Radio,Search,ShieldCheck,SlidersHorizontal,Waves,X,Satellite,Droplets,Info,RefreshCw,Clock3} from 'lucide-react';
import registry from '@/data/source-registry.json';
import {ageLabel,bangkokDate,bangkokTime,contains,freshness,metricColor,metricLabel,metricUnit,metricValue} from '@/lib/semantics';
import {damFreshness,damInArea,reportDate} from '@/lib/dams';
import DamPanel from './dam-panel';
import GaugePanel from './gauge-panel';
import RainPanel from './rain-panel';
import {loadRainSnapshot} from '@/lib/rain-client';
import {gaugeInArea,gaugeQueryFreshness} from '@/lib/gauges';
import WarningPanel from './warning-panel';
import FloodPanel from './flood-panel';
import {loadFloodSnapshot} from '@/lib/flood-client';
import HourlyPanel from './hourly-panel';
import {remainingHours,hourlyValue,hourlyFreshness,hourLabel} from '@/lib/hourly';
import {useTimeTheme} from './time-theme';
import {dashboardDates,dashboardMode,type DashboardMode} from '@/lib/dashboard-mode';
import {floodInArea,floodQueryFreshness,floodRecordsInArea,floodScopeLabel,floodResultCount} from '@/lib/floods';
import {warningFreshness,warningInArea,warningMapRecords,warningState} from '@/lib/warnings';
import type {Area,DamSnapshot,FloodSnapshot,Forecast,Metric,Snapshot,Source,WarningSnapshot,HourlySnapshot,GaugeSnapshot,RainSnapshot} from '@/lib/types';
const MapView=dynamic(()=>import('./map/map-view'),{ssr:false,loading:()=> <div className="map-loading"><Compass size={28}/><span>Preparing Thailand map…</span></div>});
const ProvinceOverview=dynamic(()=>import('./province-overview'));
const empty:Snapshot={records:[],status:null,storage:'unconfigured',error:null,freshness:'UNKNOWN'};
const emptyRain:RainSnapshot={feed:null,records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE'};
const emptyGauges:GaugeSnapshot={feed:null,records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE'};
const emptyDams:DamSnapshot={records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE'};
const emptyWarnings:WarningSnapshot={feed:null,records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE'};
const emptyHourly:HourlySnapshot={records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE'};
const emptyFloods:FloodSnapshot={feed:null,records:[],health:null,storage:'unconfigured',error:null,freshness:'UNAVAILABLE',query_freshness:'UNAVAILABLE'};

export default function Dashboard({areas}:{areas:Area[]}){
  const [provincesOpen,setProvincesOpen]=useState(false);
  const [geographyMode,setGeographyMode]=useState<'administrative'|'basin'>('administrative');
  const [rainSnapshot,setRainSnapshot]=useState<RainSnapshot>(emptyRain),[showRain,setShowRain]=useState(false),[selectedRain,setSelectedRain]=useState<string|null>(null);
  const rainRef=useRef<RainSnapshot>(emptyRain);
  const rightPanelRef=useRef<HTMLElement>(null);
  const lookup=useMemo(()=>new Map(areas.map(a=>[a.id,a])),[areas]);
  const [selected,setSelected]=useState('TH'),[search,setSearch]=useState(''),[snapshot,setSnapshot]=useState<Snapshot>(empty),[loading,setLoading]=useState(true);
  const [damSnapshot,setDamSnapshot]=useState<DamSnapshot>(emptyDams),[showDams,setShowDams]=useState(false),[selectedDam,setSelectedDam]=useState<string|null>(null);
  const [gaugeSnapshot,setGaugeSnapshot]=useState<GaugeSnapshot>(emptyGauges),[showGauges,setShowGauges]=useState(false),[selectedGauge,setSelectedGauge]=useState<string|null>(null),[gaugeLoading,setGaugeLoading]=useState(true);
  const gaugeRef=useRef<GaugeSnapshot>(emptyGauges);
  const [warningSnapshot,setWarningSnapshot]=useState<WarningSnapshot>(emptyWarnings),[showWarnings,setShowWarnings]=useState(true),[selectedWarning,setSelectedWarning]=useState<string|null>(null);
  const [floodSnapshot,setFloodSnapshot]=useState<FloodSnapshot>(emptyFloods),[showFloods,setShowFloods]=useState(false),[selectedFlood,setSelectedFlood]=useState<string|null>(null);
  const floodSnapshotRef=useRef<FloodSnapshot>(emptyFloods);
  const [floodLoading,setFloodLoading]=useState(true);
  const [metric,setMetric]=useState<Metric>('rainfall_mm'),[selectedDate,setSelectedDate]=useState<string|null>(null),[todayMode,setTodayMode]=useState<DashboardMode>('situation'),[rainfall,setRainfall]=useState(true),[is3d,setIs3d]=useState(false),[terrain,setTerrain]=useState(true),[extrude,setExtrude]=useState(false),[opacity,setOpacity]=useState(74);
  const [activeEvidence,setActiveEvidence]=useState<'tmd'|'gistda'|'rid'|'thaiwater'|'thaiwater_rain'>('tmd');
  const [sourcesOpen,setSourcesOpen]=useState(false),[leftOpen,setLeftOpen]=useState(false),[rightOpen,setRightOpen]=useState(false),[refresh,setRefresh]=useState(0);
  const {now,theme}=useTimeTheme(),clock=now??0,today=bangkokDate(clock),date=selectedDate??today;
  const mode=dashboardMode(date,today,todayMode),forecastVisible=mode!=='situation'&&geographyMode==='administrative';
  const setDate=(value:string)=>setSelectedDate(value===today?null:value);
  const [hourlySnapshot,setHourlySnapshot]=useState<HourlySnapshot>(emptyHourly),[selectedHour,setSelectedHour]=useState(''),[hourlyLoading,setHourlyLoading]=useState(false),[hourlyChecked,setHourlyChecked]=useState(false);
  const sourceOpener=useRef<HTMLButtonElement|null>(null);
  const openSources=(event:ReactMouseEvent<HTMLButtonElement>)=>{sourceOpener.current=event.currentTarget;setSourcesOpen(true);};
  useEffect(()=>{
    if(!sourcesOpen)return;
    // Capture the actual opener before the modal's autoFocus runs. Reading
    // activeElement here captures the modal's close button after mounting.
    const previous=sourceOpener.current;
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
    return()=>{document.removeEventListener('keydown',handle);if(previous?.isConnected)previous.focus({preventScroll:true});};
  },[sourcesOpen]);
  const area=lookup.get(selected)??lookup.get('TH')!;
  useEffect(()=>{rightPanelRef.current?.scrollTo({top:0,behavior:'auto'});},[area.id,activeEvidence,selectedGauge,selectedRain,selectedDam]);
  useEffect(()=>{
    let active=true;setLoading(true);
    fetch('/api/overview',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(value=>{
      if(!active)return;setSnapshot(value);
    }).catch(()=>{if(active)setSnapshot({...empty,error:'Weather snapshot is temporarily unavailable',freshness:'UNAVAILABLE'});}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[refresh]);
  useEffect(()=>{
    let active=true;
    fetch('/api/dams',{cache:'no-store'}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(value=>{if(active)setDamSnapshot(value);})
      .catch(()=>{if(active)setDamSnapshot({...emptyDams,error:'RID report snapshot is temporarily unavailable'});});
    return()=>{active=false;};
  },[refresh]);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const load=()=>fetch('/api/warnings',{cache:'no-store',signal:controller.signal}).then(async r=>{if(!r.ok)throw Error();return r.json();})
      .then(value=>{if(active)setWarningSnapshot(value);}).catch(()=>{if(active)setWarningSnapshot({...emptyWarnings,error:'TMD CAP snapshot is temporarily unavailable'});});
    void load();const timer=setInterval(load,300000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh]);
  useEffect(()=>{
    if(geographyMode==='basin'){setFloodSnapshot(emptyFloods);setFloodLoading(false);return;}
    const controller=new AbortController();let active=true;
    const mode=showFloods?'detail':'summary';
    if(floodSnapshotRef.current.scope?.area_id!==area.id||floodSnapshotRef.current.scope?.mode!==mode)setFloodSnapshot(emptyFloods);
    const load=()=>{setFloodLoading(true);return loadFloodSnapshot(controller.signal,fetch,floodSnapshotRef.current,{areaId:area.id,mode})
      .then(value=>{if(active){floodSnapshotRef.current=value;setFloodSnapshot(value);}}).catch(()=>{if(active){
        const previous=floodSnapshotRef.current;
        setFloodSnapshot(previous.feed&&previous.scope?.area_id===area.id&&previous.scope.mode===mode?{...previous,health:{...previous.health,status:'FAILED'},query_freshness:'DELAYED',error:'GISTDA refresh failed; showing the last complete three-day product.'}:{...emptyFloods,error:'GISTDA three-day product is temporarily unavailable'});
      }}).finally(()=>{if(active)setFloodLoading(false);});};
    void load();const timer=setInterval(load,300000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh,area.id,showFloods,geographyMode]);
  const hours=remainingHours(hourlySnapshot.records,clock,hourlySnapshot.available_hours),activeHour=hours.find(h=>h.valid_end===selectedHour)??hours[0];
  const requestedEnd=hours.some(h=>h.valid_end===selectedHour)?selectedHour:'',hourClock=Math.floor(clock/3600000);
  useEffect(()=>{
    if(mode!=='hourly'||geographyMode==='basin')return;
    const controller=new AbortController();let active=true;
    const hourlyUrl='/api/hourly'+(requestedEnd?'?valid_end='+encodeURIComponent(requestedEnd):'');
    const load=()=>{setHourlyLoading(true);return fetch(hourlyUrl,{cache:'no-store',signal:controller.signal}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(value=>{if(active){setHourlySnapshot(value);setHourlyChecked(true);}}).catch(()=>{if(active){setHourlySnapshot({...emptyHourly,error:'Hourly forecast is temporarily unavailable.'});setHourlyChecked(true);}}).finally(()=>{if(active)setHourlyLoading(false);});};
    void load();const timer=setInterval(load,300000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh,mode,requestedEnd,hourClock,geographyMode]);

  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const load=async()=>{
      setGaugeLoading(true);
      try{
        const response=await fetch('/api/gauges',{cache:'no-store',signal:controller.signal});
        if(!response.ok)throw Error();const value=await response.json() as GaugeSnapshot;
        if(active){gaugeRef.current=value;setGaugeSnapshot(value);}
      }catch{if(active)setGaugeSnapshot({...gaugeRef.current,error:'Station API read failed; retaining the last complete response.'});}
      finally{if(active)setGaugeLoading(false);}
    };
    void load();const timer=setInterval(load,300000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh]);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const load=async()=>{try{const value=await loadRainSnapshot(rainRef.current,showRain,controller.signal);if(active){rainRef.current=value;setRainSnapshot(value);}}
      catch{if(active)setRainSnapshot({...rainRef.current,error:'Rain station API read failed; retaining the previous response.'});}};
    void load();const timer=setInterval(load,300000);return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh,showRain]);
  const rainStatus=gaugeQueryFreshness(rainSnapshot.feed,clock,rainSnapshot.health?.status==='FAILED'||!!rainSnapshot.error);
  const rainInScope=useMemo(()=>rainSnapshot.records.filter(r=>gaugeInArea(r,area)),[rainSnapshot.records,area]);
  const gaugeStatus=gaugeQueryFreshness(gaugeSnapshot.feed,clock,gaugeSnapshot.health?.status==='FAILED'||!!gaugeSnapshot.error);
  const gaugesInScope=useMemo(()=>gaugeSnapshot.records.filter(row=>gaugeInArea(row,area)),[gaugeSnapshot.records,area]);
  const mapStationRows=useMemo(()=>[...(showGauges?gaugesInScope:[]),...(showRain?rainInScope:[])],[showGauges,gaugesInScope,showRain,rainInScope]);
  const hourlyStatus=hourlyFreshness(hourlySnapshot.records,clock,hourlySnapshot.health?.status==='FAILED');
  const displayStatus=mode==='hourly'?hourlyStatus:freshness(snapshot.records,clock);
  const displayUnit=mode==='hourly'?'mm / 1h':'mm / 24h';
  const status=freshness(snapshot.records,clock);
  const ridStatus=damFreshness(damSnapshot.records,clock);
  const tmdStatus=warningFreshness(warningSnapshot.feed,clock,warningSnapshot.health?.status==='FAILED');
  const gistdaStatus=floodQueryFreshness(floodSnapshot.feed,clock,floodSnapshot.health?.status==='FAILED');
  const floodInScope=floodInArea(area,floodSnapshot.feed),floodScope=floodScopeLabel(floodSnapshot.feed);
  const floodsInScope=useMemo(()=>floodRecordsInArea(floodSnapshot,area),[floodSnapshot,area]);
  const mapFloods=useMemo(()=>showFloods?floodsInScope:[],[showFloods,floodsInScope]);
  const warningsInScope=useMemo(()=>warningSnapshot.records.filter(r=>warningInArea(r,area,areas)),[warningSnapshot.records,area,areas]);
  const validWarnings=warningsInScope.filter(r=>warningState(r,warningSnapshot.records,clock)==='CURRENT').length;
  const mapWarnings=useMemo(()=>showWarnings?warningMapRecords(warningSnapshot.records,selectedWarning,tmdStatus,clock).filter(r=>warningInArea(r,area,areas)):[],[showWarnings,warningSnapshot.records,selectedWarning,tmdStatus,clock,area,areas]);
  const damsInScope=useMemo(()=>damSnapshot.records.filter(d=>damInArea(d,area)),[damSnapshot.records,area]);
  const availableSources=Number(snapshot.records.length>0)+Number(damSnapshot.records.length>0)+Number(warningSnapshot.feed!==null)+Number(floodSnapshot.feed!==null)+Number(hourlySnapshot.records.length>0)+Number(gaugeSnapshot.feed!==null)+Number(rainSnapshot.feed!==null);
  const dateLabel=date?`${date===bangkokDate(clock)?'Today · ':''}${new Date(date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short',year:'numeric'})}`:'No selected forecast date';
  const recordsById=useMemo(()=>new Map(snapshot.records.map(r=>[r.location_id,r])),[snapshot.records]);
  const current=recordsById.get(area.id);
  const scope=useMemo(()=>snapshot.records.filter(r=>{const a=lookup.get(r.location_id);return a&&contains(area,a);}),[snapshot.records,area,lookup]);
  const dates=dashboardDates(clock);
  const availableDates=new Set(snapshot.records.flatMap(r=>r.valid_periods.map(p=>p.date)));
  const results=search.trim()?areas.filter(a=>a.level!=='national'&&`${a.name} ${a.name_th} ${a.id}`.toLowerCase().includes(search.toLowerCase())).slice(0,8):[];
  const children=areas.filter(a=>geographyMode==='basin'?a.level==='basin':a.level!=='basin'&&a.parent_id===area.id).sort((a,b)=>a.name.localeCompare(b.name));
  const trail:Area[]=[];let parent:Area|undefined=area;while(parent){trail.unshift(parent);parent=parent.parent_id?lookup.get(parent.parent_id):undefined;}
  const select=(id:string)=>{if(!lookup.has(id))return;setSelected(id);if(id.startsWith('TH-B-')){setGeographyMode('basin');setShowWarnings(false);setShowFloods(false);setTodayMode('situation');setSelectedDate(today);}else if(id!=='TH')setGeographyMode('administrative');setSelectedRain(null);setSelectedGauge(null);setSelectedDam(null);setSelectedWarning(null);setSelectedFlood(null);setSearch('');setLeftOpen(false);setRightOpen(true);};
  const selectRain=(id:string|null)=>{setActiveEvidence('thaiwater_rain');setSelectedRain(id);setSelectedGauge(null);setShowRain(true);setRightOpen(true);setLeftOpen(false);};
  const chooseGeography=(value:'administrative'|'basin')=>{setGeographyMode(value);select('TH');setTodayMode('situation');setSelectedDate(today);setLeftOpen(true);setRightOpen(false);if(value==='basin'){setShowWarnings(false);setShowFloods(false);setShowGauges(true);setShowDams(true);setActiveEvidence('thaiwater');}};
  const selectGauge=(id:string|null)=>{setSelectedRain(null);setActiveEvidence('thaiwater');setSelectedGauge(id);setShowGauges(true);setRightOpen(true);setLeftOpen(false);};
  const selectDam=(id:string)=>{setActiveEvidence('rid');setSelectedDam(id);setSelectedWarning(null);setShowDams(true);setRightOpen(true);setLeftOpen(false);};
  const selectWarning=(id:string|null)=>{setActiveEvidence('tmd');setSelectedWarning(id);setSelectedDam(null);setShowWarnings(true);setRightOpen(true);setLeftOpen(false);};
  const selectFlood=(id:string|null)=>{setActiveEvidence('gistda');setSelectedFlood(id);setSelectedWarning(null);setSelectedDam(null);setShowFloods(true);setRightOpen(true);setLeftOpen(false);};
  const rainfallValues=(mode==='hourly'?hourlySnapshot.records.filter(r=>contains(area,lookup.get(r.location_id)!)).map(r=>hourlyValue(r,activeHour?.valid_end??'','rainfall_mm')):scope.map(r=>metricValue(r,date,'rainfall_mm'))).filter((v):v is number=>v!==null);
  const max=rainfallValues.length?Math.max(...rainfallValues):null;
  const currentPeriod=current?.valid_periods.find(p=>p.date===date);
  const oldestFetch=snapshot.records.length?snapshot.records.map(r=>r.fetched_at).sort()[0]:null;
  const firstValid=snapshot.records[0]?.valid_periods[0]?.valid_start;
  function download(){
    const blob=new Blob([JSON.stringify({area:area.id,date,source:'Open-Meteo',records:scope},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`thailand-weather-${area.id}-${date||'unavailable'}.json`;a.click();URL.revokeObjectURL(url);
  }
  if(now===null)return <main className="dashboard"><p>Preparing Bangkok situation view…</p></main>;
  return <main className="dashboard">
    <a href="#area-navigation" className="skip-link">Skip map to area navigation</a>
    <header className="topbar"><a className="brand" href="/" aria-label="Thailand Hazard Intelligence home"><span className="brand-mark"><Layers3 size={24}/></span><span><b>THAILAND <em>HAZARD INTELLIGENCE</em></b><small>UNIFIED WEATHER & WATER MONITORING</small></span></a>
      <div className="search-wrap"><Search size={17}/><input aria-label="Search area" placeholder="Search province, district, or Thai name…" value={search} onChange={e=>setSearch(e.target.value)}/><kbd>⌕</kbd>
        {search&&<div className="search-results">{results.length?results.map(a=><button key={a.id} onClick={()=>select(a.id)}><MapPin size={14}/><span>{a.name}<small>{a.name_th} · {a.level}</small></span><ChevronRight size={14}/></button>):<p>No matching areas</p>}</div>}
      </div>
      <button className="source-top" onClick={openSources}><span className={`status-dot ${status.toLowerCase()}`}/><span>Source status<small>{availableSources} available · {registry.length-availableSources} pending/unavailable</small></span><ChevronDown size={14}/></button>
    </header>
    <div className="situation-title"><div><p className="eyebrow">SITUATION OVERVIEW</p><h1>From national outlook to local understanding.</h1></div><span className="monitoring-badge"><ShieldCheck size={14}/> Monitoring · source-specific evidence</span></div>
    <section className="mode-bar" aria-label="Dashboard mode"><div><b>{mode==='situation'?'Situation Monitoring':mode==='hourly'?"Today's Hourly Forecast":'Daily Forecast'}</b><span>{dateLabel} · {theme.toUpperCase()} theme · Bangkok clock</span></div>{date===today&&<div className="mode-actions"><button aria-pressed={mode==='situation'} onClick={()=>setTodayMode('situation')}>Situation today</button><button disabled={geographyMode==='basin'} aria-pressed={mode==='daily'} onClick={()=>setTodayMode('daily')}>Today's daily forecast</button><button disabled={geographyMode==='basin'} aria-pressed={mode==='hourly'} onClick={()=>{setTodayMode('hourly');setRightOpen(true);setLeftOpen(false);}}>Today's hourly forecast</button></div>}</section>
    <p className="mode-note" role="status">{mode==='daily'&&!availableDates.has(date)?`No daily forecast is available for ${date}. `:null}{mode==='situation'?'Latest source-specific reports and warnings; source dates may differ. Missing data does not establish safe conditions.':'FORECAST · Agency overlays retain their own source dates; they are not forecasts for the selected day.'}</p>
    <section className="summary-grid" aria-label="Situation overview">
      {mode==='situation'?<div className="summary-card"><span className="summary-icon teal"><Waves size={21}/></span><div><label>River level observations</label><strong>{gaugeSnapshot.feed?gaugesInScope.length:'—'}<small>{gaugeSnapshot.feed?'station reports':gaugeLoading?'Loading':'Unavailable'}</small></strong><p>HII / ThaiWater · observation timezone unknown</p></div><span className="mini-tag">OBSERVATIONS</span></div>:<div className="summary-card"><span className="summary-icon teal"><CloudRain size={21}/></span><div><label>Forecast rainfall · {mode==='hourly'&&activeHour?hourLabel(activeHour):dateLabel}</label><strong>{max===null?'—':max.toFixed(1)}<small>{max===null?'No data':displayUnit}</small></strong><p>{max===null?'Waiting for a validated snapshot':`Maximum point forecast · ${area.level==='national'?'Thailand':area.name}`}</p></div><span className="mini-tag">FORECAST</span></div>}
      <div className="summary-card"><span className="summary-icon blue"><Radio size={21}/></span><div><label>TMD CAP messages</label><strong>{geographyMode==='basin'?'—':warningSnapshot.feed?validWarnings:'—'}<small>{geographyMode==='basin'?'Province references':warningSnapshot.feed?'within validity window':'Unavailable'}</small></strong><p>{geographyMode==='basin'?'TMD · ใช้ตัวกรองจังหวัด':warningSnapshot.feed?`${warningsInScope.length} latest-feed messages · ${tmdStatus}`:'Awaiting published CAP feed'}</p></div></div>
      <div className="summary-card"><span className="summary-icon violet"><Droplets size={21}/></span><div><label>Reservoir reports</label><strong>{damSnapshot.records.length?damsInScope.length:'—'}<small>{damSnapshot.records.length?'dam points':ridStatus}</small></strong><p>{damSnapshot.records.length?`RID daily report · ${reportDate(damSnapshot.records[0].report_date)}`:'RID · awaiting published report'}</p></div></div>
      <div className="summary-card"><span className="summary-icon sand"><Satellite size={21}/></span><div><label>Satellite product results</label><strong>{floodSnapshot.feed&&floodInScope?floodResultCount(floodSnapshot,area)??'—':'—'}<small>{geographyMode==='basin'?'Province references':!floodSnapshot.feed?(floodLoading?'Loading area query':'Awaiting snapshot'):floodInScope?'returned features':'Outside scope'}</small></strong><p>{geographyMode==='basin'?'GISTDA · ยังไม่จับคู่ขอบเขตลุ่มน้ำ':`GISTDA · 3 days · ${floodScope} · acquisition unknown`}</p></div></div>
    </section>
    <div className="province-toggle-bar"><button aria-expanded={provincesOpen} onClick={()=>setProvincesOpen(value=>!value)}><Activity size={15}/> เปรียบเทียบสถานการณ์ 77 จังหวัด <ChevronDown size={14}/></button><span>พยากรณ์วันนี้ · คำเตือน · ระดับน้ำ · เขื่อน · ดาวเทียม</span></div>
    {provincesOpen&&<ProvinceOverview onClose={()=>setProvincesOpen(false)} onSelect={id=>{select(id);setProvincesOpen(false);}}/>}
    <section className="map-workspace">
      <div className="workspace-bar"><nav aria-label="Geography breadcrumb">{trail.map((a,i)=><span key={a.id}>{i>0&&<ChevronRight size={12}/>}<button onClick={()=>select(a.id)} aria-current={i===trail.length-1?'location':undefined}>{a.level==='national'?<><Compass size={14}/> Thailand</>:a.name}</button></span>)}</nav><div className="view-controls"><button className="mobile-control" onClick={()=>setLeftOpen(!leftOpen)}><SlidersHorizontal size={15}/> Layers</button><button className={is3d?'':'active'} aria-pressed={!is3d} onClick={()=>setIs3d(false)}>2D</button><button className={is3d?'active':''} aria-pressed={is3d} onClick={()=>setIs3d(true)}>3D</button><button className="mobile-control" onClick={()=>setRightOpen(!rightOpen)}><Info size={15}/> Area</button></div></div>
      {geographyMode==='basin'&&<p className="basin-context-note">22 ลุ่มน้ำจาก DDPM GIS · จับคู่จุดสถานีและเขื่อนเฉพาะภายในขอบเขตที่ยืนยันได้ จุดใกล้ขอบ/ชายฝั่งยังไม่จับคู่ ขอบเขตย่อเพื่อแสดงผล ไม่ได้อนุมานทางน้ำหรือลำดับต้นน้ำ–ปลายน้ำ · คำเตือนและดาวเทียมยังใช้ตัวกรองจังหวัด</p>}
      <div className="workspace-body">
        <aside className={`left-panel ${leftOpen?'mobile-open':''}`} aria-label="Layers and geography"><div className="panel-heading"><h2><Layers3 size={16}/> Map layers</h2><button className="mobile-close" aria-label="Close layers" onClick={()=>setLeftOpen(false)}><X size={16}/></button></div>
          <p className="panel-description">One map. Independent sources.</p>
          <label className="layer enabled"><CloudRain size={17}/><span><b>Weather forecast</b><small>Open-Meteo</small></span><input type="checkbox" checked={forecastVisible&&rainfall} disabled={!forecastVisible} onChange={e=>setRainfall(e.target.checked)}/></label>
          <div className="metric-controls"><label htmlFor="metric">Display metric</label><select id="metric" value={metric} onChange={e=>setMetric(e.target.value as Metric)}><option value="rainfall_mm">Rainfall · {displayUnit}</option><option value="rain_probability_pct">Chance of rain · %</option></select><label className="opacity-label">Layer opacity <span>{opacity}%</span><input aria-label="Layer opacity" type="range" min="15" max="100" value={opacity} onChange={e=>setOpacity(+e.target.value)}/></label></div>
          <label className={`layer ${damSnapshot.records.length?'enabled':'planned'}`}><Droplets size={17}/><span><b>Reservoirs & dams</b><small>RID · {damSnapshot.records.length?'daily storage report':'awaiting first report'}</small></span><input aria-label="RID reservoir reports" type="checkbox" checked={showDams} disabled={!damSnapshot.records.length} onChange={e=>{setShowDams(e.target.checked);setSelectedDam(null);if(e.target.checked){setActiveEvidence('rid');setRightOpen(true);setLeftOpen(false);}}}/></label>
          <label className={`layer ${warningSnapshot.feed?'enabled':'planned'}`}><Radio size={17}/><span><b>Agency warnings</b><small>TMD · {warningSnapshot.feed?'CAP messages':'awaiting first feed'}</small></span><input aria-label="TMD CAP messages" type="checkbox" checked={showWarnings} disabled={!warningSnapshot.feed||geographyMode==='basin'} onChange={e=>{setShowWarnings(e.target.checked);setSelectedWarning(null);if(e.target.checked){setActiveEvidence('tmd');setRightOpen(true);setLeftOpen(false);}}}/></label>
          <label className={`layer ${floodSnapshot.feed?'enabled':'planned'}`}><Satellite size={17}/><span><b>Flood observations · 3 days</b><small>GISTDA · 3 days · {floodScope} · acquisition unknown</small></span><input aria-label="Flood observations" type="checkbox" checked={showFloods} disabled={!floodSnapshot.feed||geographyMode==='basin'} onChange={e=>{setShowFloods(e.target.checked);setSelectedFlood(null);if(e.target.checked){setActiveEvidence('gistda');setRightOpen(true);setLeftOpen(false);}}}/></label>
          <label className={`layer ${gaugeSnapshot.feed?'enabled':'planned'}`}><Waves size={17}/><span><b>River level stations</b><small>HII / ThaiWater · source time qualified</small></span><input aria-label="HII river level stations" type="checkbox" checked={showGauges} disabled={!gaugeSnapshot.feed} onChange={event=>{setShowGauges(event.target.checked);setSelectedGauge(null);if(event.target.checked){setActiveEvidence('thaiwater');setRightOpen(true);setLeftOpen(false);}}}/></label>
          <label className={`layer ${rainSnapshot.feed?'enabled':'planned'}`}><CloudRain size={17}/><span><b>Observed rain stations</b><small>HII · mm/24h · observation timezone unknown</small></span><input aria-label="HII observed rain stations" type="checkbox" checked={showRain} disabled={!rainSnapshot.feed} onChange={e=>{setShowRain(e.target.checked);setSelectedRain(null);if(e.target.checked)selectRain(null);}}/></label>
          {showGauges&&showRain&&<p className="gauge-map-note">ตัวเลขกลุ่มนับรายการระดับน้ำและฝนแยกประเภท บางสถานีใช้พิกัดเดียวกัน</p>}
          <div className="terrain-controls"><label className="check-line"><Mountain size={16}/><span>Terrain in 3D</span><input type="checkbox" checked={terrain} onChange={e=>setTerrain(e.target.checked)}/></label><label className="check-line"><Layers3 size={16}/><span>Metric extrusion</span><input type="checkbox" checked={extrude} disabled={!['province','district'].includes(area.level)} onChange={e=>setExtrude(e.target.checked)}/></label><p>Extrusion height scales the selected forecast metric. It does not represent water depth.</p></div>
          <div className="geography-section" id="area-navigation"><h2><MapPin size={16}/> Explore geography</h2><div className="geo-mode"><button className={geographyMode==='administrative'?'active':''} onClick={()=>chooseGeography('administrative')}>Administrative</button><button className={geographyMode==='basin'?'active':''} onClick={()=>chooseGeography('basin')}>Basin · 22</button></div>
            {area.level!=='national'&&<button className="back-national" onClick={()=>select('TH')}><ArrowLeft size={13}/> Back to Thailand</button>}
            <p className="list-label">{geographyMode==='basin'?'22 ลุ่มน้ำ · DDPM / ONWR context':area.level==='national'?'REGIONS · 6-REGION CLASSIFICATION':area.level==='region'?'PROVINCES':area.level==='province'?'DISTRICTS':'SELECTED DISTRICT'}</p>
            <div className="area-list">{children.length?children.map(a=><button key={a.id} onClick={()=>select(a.id)}><span>{a.name}<small>{a.name_th}</small></span><ChevronRight size={14}/></button>):<div className="selected-district"><Check size={15}/>{area.name}<small>{area.id}</small></div>}</div>
          </div>
          <div className="left-footer"><Link href="/health"><Activity size={13}/> Data health <ArrowUpRight size={12}/></Link><a href="/methodology"><Info size={13}/> Data & methodology <ArrowUpRight size={12}/></a></div>
        </aside>
        <div className="map-column"><MapView geographyMode={geographyMode} area={area} areas={areas} records={snapshot.records} gauges={mapStationRows} showGauges={showGauges||showRain} selectedGauge={selectedRain??selectedGauge} onSelectGauge={id=>id.startsWith('THR-')?selectRain(id):selectGauge(id)} dams={damsInScope} showDams={showDams} damFreshness={ridStatus} selectedDam={selectedDam} onSelectDam={selectDam} warnings={mapWarnings} onSelectWarning={selectWarning} floods={mapFloods} floodFreshness={gistdaStatus} selectedFlood={selectedFlood} onSelectFlood={selectFlood} date={date} metric={metric} is3d={is3d} terrain={terrain} theme={theme} hourly={mode==='hourly'?{records:hourlySnapshot.records,validEnd:activeHour?.valid_end??''}:null} validTimeLabel={mode==='hourly'?(activeHour?hourLabel(activeHour):'No hourly interval available'):`${date} · ICT 00:00–24:00`} rainfall={forecastVisible&&rainfall} extrude={extrude} opacity={opacity} freshness={displayStatus} onSelect={select}/>
          {showDams&&damSnapshot.records.length>0&&<div className="dam-map-label">◆ RID daily storage · {reportDate(damSnapshot.records[0].report_date)} · {ridStatus}</div>}
          {showWarnings&&warningSnapshot.feed&&<div className="warning-map-label" style={{top:showDams?104:72}}>TMD CAP · {selectedWarning&&mapWarnings.some(r=>r.display_state!=='CURRENT')?'PREVIOUS / NON-CURRENT MESSAGE':`${validWarnings} within validity window · ${tmdStatus}${tmdStatus==='FRESH'?'':' · gray references'}`} · checked {bangkokTime(warningSnapshot.feed.fetched_at)}</div>}
          {showFloods&&floodSnapshot.feed&&<div className="flood-map-label" style={{top:74+Number(showDams)*34+Number(showWarnings)*44}}>GISTDA · ย้อนหลัง 3 วัน · {floodScope} · {floodInScope?`${floodsInScope.length} returned features`:'outside selected area'} · acquisition time not supplied</div>}
          {forecastVisible&&<div className="legend"><div><b>{metricLabel(metric)}</b><span>{metricUnit(metric,mode==='hourly'?'hourly':'daily')} · representative point</span></div><div className="legend-scale">{(metric==='rainfall_mm'?(mode==='hourly'?[0,.2,1,5,10]:[0,1,10,25,50]):[0,20,40,60,80]).map(v=><span key={v}><i style={{background:`rgba(${metricColor(v,metric,mode==='hourly'?'hourly':'daily').slice(0,3).join(',')},1)`}}/>{v}{v===(metric==='rainfall_mm'?(mode==='hourly'?10:50):80)?'+':''}</span>)}<span><i className="no-data"/>No data / stale</span></div></div>}
        </div>
        <aside ref={rightPanelRef} className={`right-panel ${rightOpen?'mobile-open':''}`} aria-label="Area intelligence"><div className="panel-heading"><h2>Area intelligence</h2><button className="mobile-close" aria-label="Close area intelligence" onClick={()=>setRightOpen(false)}><X size={16}/></button></div>
          {mode==='hourly'&&<HourlyPanel loading={hourlyLoading} area={area} snapshot={hourlySnapshot} now={clock} selectedEnd={activeHour?.valid_end??''} onHour={setSelectedHour}/>}
          {(['tmd','gistda','rid','thaiwater','thaiwater_rain'] as const).filter(id=>id==='tmd'?showWarnings:id==='gistda'?showFloods:id==='thaiwater'?showGauges:id==='thaiwater_rain'?showRain:showDams)
            .sort((a,b)=>Number(b===activeEvidence)-Number(a===activeEvidence)).map(id=>id==='tmd'
              ?<WarningPanel key={id} area={area} areas={areas} snapshot={warningSnapshot} freshness={tmdStatus} selectedId={selectedWarning} now={clock} onSelect={selectWarning}/>
              :id==='gistda'?<FloodPanel key={`${id}:${area.id}`} area={area} snapshot={floodSnapshot} queryFreshness={gistdaStatus} selectedId={selectedFlood} onSelect={selectFlood} onArea={select}/>
              :id==='thaiwater_rain'?<RainPanel key={`${id}:${area.id}`} area={area} snapshot={rainSnapshot} freshness={rainStatus} selectedId={selectedRain} onSelect={selectRain}/>:id==='thaiwater'?<GaugePanel key={`${id}:${area.id}`} area={area} snapshot={gaugeSnapshot} queryFreshness={gaugeStatus} selectedId={selectedGauge} loading={gaugeLoading} onSelect={selectGauge}/>:<DamPanel key={id} area={area} snapshot={damSnapshot} freshness={ridStatus} selectedId={selectedDam} onSelect={selectDam} onClose={()=>setSelectedDam(null)}/>)}
          {mode==='situation'&&<section className="situation-evidence" aria-label="Situation source clocks"><h3>Latest available situation</h3><p>Each source keeps its own date and coverage.</p><button disabled={!rainSnapshot.feed} onClick={()=>selectRain(null)}>HII observed rain stations · {rainSnapshot.feed?.record_count??"—"}<small>{rainStatus} query · observation timezone unknown</small></button><button disabled={!gaugeSnapshot.feed} onClick={()=>selectGauge(null)}>HII river level stations · {gaugeSnapshot.feed?.record_count??"—"}<small>{gaugeStatus} query · observation timezone unknown</small></button><button disabled={geographyMode==='basin'} onClick={()=>{setShowWarnings(true);setActiveEvidence('tmd');}}>TMD official warnings · {tmdStatus}<small>Checked {bangkokTime(warningSnapshot.feed?.fetched_at)}</small></button><button onClick={()=>{setShowDams(true);setActiveEvidence('rid');}}>RID reported storage · {ridStatus}<small>Report {damSnapshot.records[0]?.report_date??'unavailable'}</small></button><button disabled={geographyMode==='basin'} onClick={()=>{setShowFloods(true);setActiveEvidence('gistda');}}>GISTDA latest retrieved product<small>{floodSnapshot.feed?`${gistdaStatus} query · acquisition unknown`:'UNAVAILABLE'}</small></button></section>}
          {area.level==='national'?<div className="area-empty"><span className="empty-icon"><MapPin size={26}/></span><h3>A closer look, in context.</h3><p>Select a region, province or district to bring its weather and water evidence together.</p><div className="journey">Thailand <ChevronRight size={12}/> Region <ChevronRight size={12}/> Local</div></div>:<>
          <div className="selected-area"><span className="eyebrow">{area.level.toUpperCase()}</span><h3>{area.name}</h3><p>{area.name_th} <span>{area.id}</span></p></div>
          {mode==='daily'&&<div className="evidence-card"><div className="evidence-heading"><CloudRain size={16}/><b>Weather outlook</b><span className="mini-tag">FORECAST</span></div>
            {current?<><div className="area-value">{currentPeriod?.rainfall_mm==null?'—':currentPeriod.rainfall_mm.toFixed(1)}<span>mm / 24h</span></div><p className="value-caption">Forecast rainfall · {date}</p><div className="weather-pair"><span>Chance of rain<b>{currentPeriod?.rain_probability_pct==null?'No data':`${currentPeriod.rain_probability_pct}%`}</b></span><span>Temperature<b>{currentPeriod?.temp_min_c==null||currentPeriod?.temp_max_c==null?'No data':`${currentPeriod.temp_min_c}–${currentPeriod.temp_max_c}°C`}</b></span></div>
            <div className="mini-chart" aria-label="Daily forecast rainfall">{current.valid_periods.map(p=><button className={p.date===date?'active':''} key={p.date} onClick={()=>setDate(p.date)}><span>{p.rainfall_mm??'—'}</span><i style={{height:p.rainfall_mm==null?2:Math.max(3,Math.min(50,p.rainfall_mm*1.2))}}/><small>{new Date(p.date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</small></button>)}</div>
            <p className="coverage-note"><Info size={12}/>{current.spatial_method}. Requested {current.point.lat.toFixed(3)}°N, {current.point.lon.toFixed(3)}°E. Returned grid {current.model_point.lat.toFixed(3)}°N, {current.model_point.lon.toFixed(3)}°E.</p><dl className="time-details"><dt>Valid window</dt><dd>{bangkokTime(currentPeriod?.valid_start)} – {bangkokTime(currentPeriod?.valid_end)}</dd><dt>Model issue time</dt><dd>Not supplied by provider</dd><dt>Retrieved</dt><dd>{bangkokTime(current.fetched_at)}</dd><dt>Quality</dt><dd>{current.quality_status}</dd></dl></>:
            <div className="region-outlook"><strong>{scope.length}</strong><p>{scope.length?'forecast points in this region. Select a province for its point forecast.':'No forecast available for this area.'}</p></div>}
            <a className="source-link" href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather data by Open-Meteo <ArrowUpRight size={12}/></a></div>}
          <div className="unavailable-evidence"><Waves size={16}/><div><b>River level stations</b><p>{gaugeSnapshot.feed?`${gaugesInScope.length} station reports · observation timezone unknown`:gaugeLoading?'Loading station reports…':'No published station response'}</p><button className="dam-back" disabled={!gaugeSnapshot.feed} onClick={()=>selectGauge(null)}>Open station list <ArrowUpRight size={12}/></button></div></div>
          <button className="export-button" disabled={!scope.length||mode!=='daily'||geographyMode==='basin'} onClick={download}><ArrowDownToLine size={14}/> Export this area’s weather</button></>}
          <div className="freshness-card"><div><Clock3 size={15}/><b>Daily forecast freshness</b><span className={`freshness ${status.toLowerCase()}`}>{loading?'LOADING':status}</span></div><p>{snapshot.records.length?`${snapshot.records.length} of 1,005 forecast points available`:'No published weather data'}</p><small>Oldest retrieval: {bangkokTime(oldestFetch)}</small><small>First valid window: {bangkokTime(firstValid)}</small>{snapshot.status?.status==='FAILED'&&<p className="failed-run">Latest ingestion failed · showing last good data</p>}<button onClick={openSources}>View all sources <ArrowUpRight size={12}/></button></div>
        </aside>
      </div>
      <footer className="timeline"><div className="timeline-label"><Clock3 size={16}/><span><b>Situation / forecast dates</b><small>Asia/Bangkok · calendar dates</small></span></div><div className="timeline-dates">{dates.length?dates.map(d=><button disabled={geographyMode==='basin'&&d!==today} className={d===date?'active':''} key={d} onClick={()=>setDate(d)}><span>{d===today?'Today':new Date(d+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',weekday:'short'})}</span><b>{new Date(d+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short'})}</b><small>{d===today?'Situation / forecast':availableDates.has(d)?'Daily forecast':'Forecast unavailable'}</small><i/></button>):<p>{loading?'Loading available forecast windows…':'No forecast windows available'}</p>}</div><button className="refresh-button" disabled={loading} onClick={()=>setRefresh(x=>x+1)}><RefreshCw size={14} className={loading?'spin':''}/><span>Reload snapshot</span></button></footer>
    </section>
    <div className="bottomline"><span><span className={`status-dot ${status.toLowerCase()}`}/>{snapshot.storage==='local'?'Local preview · real API snapshot':snapshot.storage==='mongo'?'Latest published snapshot':'Data connection pending'}{snapshot.error?` · ${snapshot.error}`:''}</span><span>Situation awareness · consult official agency guidance <Link href="/methodology">Methodology <ArrowUpRight size={11}/></Link></span></div>
    {sourcesOpen&&<div className="modal-backdrop" onClick={()=>setSourcesOpen(false)}><section className="sources-modal" role="dialog" aria-modal="true" aria-label="Source status" onClick={e=>e.stopPropagation()}><div className="modal-heading"><div><p className="eyebrow">PROVENANCE & AVAILABILITY</p><h2>Independent sources. Clear timestamps.</h2></div><button autoFocus aria-label="Close source status" onClick={()=>setSourcesOpen(false)}><X size={20}/></button></div><p className="modal-intro">Missing data is unavailable, never an indication of normal or safe conditions. Sources update independently.</p>{(registry as Source[]).map(source=><article className="source-row" key={source.id}><div><h3>{source.organization}<span className="mini-tag">{source.state.replaceAll('_',' ')}</span></h3><p>{source.name} · {source.id==='open_meteo'?(snapshot.records.length?`${status} · ${snapshot.records.length} points`: 'UNAVAILABLE'):source.id==='open_meteo_hourly'?(hourlyChecked?`${hourlyStatus} · ${hourlySnapshot.records.length} points`:'Not checked · open Today hourly'):source.id==='thaiwater_rain'?(rainSnapshot.feed?`${rainStatus} query · ${rainSnapshot.feed.record_count} rain stations · observation age unknown`:'UNAVAILABLE'):source.id==='thaiwater'?(gaugeSnapshot.feed?`${gaugeStatus} query · ${gaugeSnapshot.feed.record_count} stations · observation age unknown`:'UNAVAILABLE'):source.id==='rid'?`${ridStatus} · ${damSnapshot.records.length} reports`:source.id==='tmd'?`${tmdStatus} · ${warningSnapshot.records.length} latest-feed messages`:source.id==='gistda'?(floodSnapshot.feed?`${gistdaStatus} query · ${floodResultCount(floodSnapshot,area)??"—"} returned · ${floodScope}`:'UNAVAILABLE'):source.status}</p><small>{source.description}</small><div className="source-meta"><span>{source.cadence}</span><span>{source.id==='open_meteo'?`Retrieved ${bangkokTime(oldestFetch)}`:source.id==='open_meteo_hourly'?`Hourly retrieved ${bangkokTime(hourlySnapshot.records[0]?.fetched_at)}`:source.id==='thaiwater_rain'?`Rain response ${bangkokTime(rainSnapshot.feed?.fetched_at)} · observation timezone unknown`:source.id==='thaiwater'?`Station response ${bangkokTime(gaugeSnapshot.feed?.fetched_at)} · observation timezone unknown`:source.id==='rid'?(damSnapshot.records.length?`Report ${reportDate(damSnapshot.records[0].report_date)}`:'Awaiting published report'):source.id==='tmd'?`Feed checked ${bangkokTime(warningSnapshot.feed?.fetched_at)}`:source.id==='gistda'?`Query checked ${bangkokTime(floodSnapshot.feed?.fetched_at)} · acquisition unknown`:'Acceptance pending'}</span></div><a href={source.url} target="_blank" rel="noreferrer">Source documentation <ArrowUpRight size={12}/></a></div></article>)}<Link className="registry-link" href="/health">Data health · สุขภาพระบบข้อมูล <ArrowUpRight size={14}/></Link><Link className="registry-link" href="/sources">Full source registry & terms <ArrowUpRight size={14}/></Link></section></div>}
  </main>;
}
