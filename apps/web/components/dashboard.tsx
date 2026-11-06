'use client';
import RadarPlayer from './radar-player';
import WorkspaceTopbar from './workspace/topbar';
import WorkspaceDialog from './workspace/dialog';
import WorkspaceRail from './workspace/rail';
import LayerControls,{type LayerOption} from './workspace/layer-controls';
import ContextInspector from './workspace/inspector';
import AreaInspector from './workspace/area-inspector';
import ForecastInspector from './workspace/forecast-inspector';
import SituationOverview from './workspace/overview';
import TimeDock from './workspace/time-dock';
import {datePresentation,visibleInspector,workspaceBackgroundAvailable,type InspectorId} from '@/lib/workspace';
import styles from './workspace/workspace.module.css';
import {emptyRadar,radarFreshness,radarVisible,type RadarSnapshot,type RadarLoad} from '@/lib/radar';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {useEffect,useMemo,useRef,useState} from 'react';
import type {MouseEvent as ReactMouseEvent} from 'react';
import {ChevronRight,Compass,Database,Layers3,Radio,Waves,X,Satellite,Droplets,Info,ArrowUpRight} from 'lucide-react';
import registry from '@/data/source-registry.json';
import {bangkokDate,bangkokTime,contains,freshness,metricColor,metricLabel,metricUnit} from '@/lib/semantics';
import {damFreshness,damInArea,reportDate} from '@/lib/dams';
import DamPanel from './dam-panel';
import GaugePanel from './gauge-panel';
import MapLegend,{type MapLegendEntry} from './map/map-legend';
import RainPanel from './rain-panel';
import {loadRainSnapshot} from '@/lib/rain-client';
import {gaugeInArea,gaugeQueryFreshness} from '@/lib/gauges';
import WarningPanel from './warning-panel';
import FloodPanel from './flood-panel';
import {loadFloodSnapshot} from '@/lib/flood-client';
import {useFloodViewport} from './use-flood-viewport';
import {viewportStatusText,type FloodMapView} from '@/lib/flood-viewport';
import HourlyPanel from './hourly-panel';
import {remainingHours,hourlyFreshness,hourLabel} from '@/lib/hourly';
import {useTimeTheme} from './time-theme';
import {effectiveBackground,type MapBackground} from '@/lib/map-layer-state';
import {dashboardDates,dashboardMode,type DashboardMode} from '@/lib/dashboard-mode';
import {floodInArea,floodQueryFreshness,floodRecordsInArea,floodScopeLabel,floodResultCount,floodWindowText} from '@/lib/floods';
import {warningFreshness,warningInArea,warningMapRecords,warningState} from '@/lib/warnings';
import type {Area,DamSnapshot,FloodSnapshot,Metric,Snapshot,Source,WarningSnapshot,HourlySnapshot,GaugeSnapshot,RainSnapshot} from '@/lib/types';
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
  const [radarSnapshot,setRadarSnapshot]=useState<RadarSnapshot>(emptyRadar),[showRadar,setShowRadar]=useState(false),[radarIndex,setRadarIndex]=useState(0),[radarOpacity,setRadarOpacity]=useState(78),[radarLoad,setRadarLoad]=useState<RadarLoad|null>(null);
  const radarFeedRef=useRef<string|null>(null);
  const [provincesOpen,setProvincesOpen]=useState(false),[overviewOpen,setOverviewOpen]=useState(false),[controlsTab,setControlsTab]=useState<'layers'|'geography'>('layers');
  const [geographyMode,setGeographyMode]=useState<'administrative'|'basin'>('administrative');
  const [rainSnapshot,setRainSnapshot]=useState<RainSnapshot>(emptyRain),[showRain,setShowRain]=useState(false),[selectedRain,setSelectedRain]=useState<string|null>(null);
  const rainRef=useRef<RainSnapshot>(emptyRain);
  const rightPanelRef=useRef<HTMLElement>(null);
  const lookup=useMemo(()=>new Map(areas.map(a=>[a.id,a])),[areas]);
  const [selected,setSelected]=useState('TH'),[snapshot,setSnapshot]=useState<Snapshot>(empty),[loading,setLoading]=useState(true);
  const [damSnapshot,setDamSnapshot]=useState<DamSnapshot>(emptyDams),[showDams,setShowDams]=useState(false),[selectedDam,setSelectedDam]=useState<string|null>(null);
  const [gaugeSnapshot,setGaugeSnapshot]=useState<GaugeSnapshot>(emptyGauges),[showGauges,setShowGauges]=useState(false),[selectedGauge,setSelectedGauge]=useState<string|null>(null),[gaugeLoading,setGaugeLoading]=useState(true);
  const gaugeRef=useRef<GaugeSnapshot>(emptyGauges);
  const [warningSnapshot,setWarningSnapshot]=useState<WarningSnapshot>(emptyWarnings),[showWarnings,setShowWarnings]=useState(true),[selectedWarning,setSelectedWarning]=useState<string|null>(null);
  const [floodSnapshot,setFloodSnapshot]=useState<FloodSnapshot>(emptyFloods),[showFloods,setShowFloods]=useState(false),[selectedFlood,setSelectedFlood]=useState<string|null>(null);
  const floodSnapshotRef=useRef<FloodSnapshot>(emptyFloods);
  const [floodWindow,setFloodWindow]=useState<import('@/lib/types').FloodWindow>('3days'),[floodGeneration,setFloodGeneration]=useState(''),[floodPage,setFloodPage]=useState(0);
  const [floodLoading,setFloodLoading]=useState(true);
  const [floodDisplayMode,setFloodDisplayMode]=useState<'viewport'|'area'>('viewport'),[floodMapView,setFloodMapView]=useState<FloodMapView|null>(null);
  const [metric,setMetric]=useState<Metric>('rainfall_mm'),[selectedDate,setSelectedDate]=useState<string|null>(null),[todayMode,setTodayMode]=useState<DashboardMode>('situation'),[rainfall,setRainfall]=useState(true),[is3d,setIs3d]=useState(false),[terrain,setTerrain]=useState(true),[extrude,setExtrude]=useState(false),[opacity,setOpacity]=useState(74);
  const [activeEvidence,setActiveEvidence]=useState<InspectorId>('area');
  const [sourcesOpen,setSourcesOpen]=useState(false),[leftOpen,setLeftOpen]=useState(false),[rightOpen,setRightOpen]=useState(false),[refresh,setRefresh]=useState(0);
  const {now,theme}=useTimeTheme(),clock=now??0,today=bangkokDate(clock),date=selectedDate??today;
  const mode=dashboardMode(date,today,todayMode),background=effectiveBackground(mode,rainfall,geographyMode,showRadar),forecastVisible=background==='daily'||background==='hourly';
  const chooseBackground=(next:MapBackground)=>{
    if(!workspaceBackgroundAvailable(next,date,today,geographyMode))return;
    setShowRadar(next==='radar');setRainfall(next==='daily'||next==='hourly');
    setTodayMode(next==='daily'||next==='hourly'?next:'situation');
    setActiveEvidence(next==='daily'||next==='hourly'?'forecast':'area');
    if(next==='daily'||next==='hourly'){setRightOpen(true);setLeftOpen(false);}
  };
  const setDate=(value:string)=>{
    const next=datePresentation(value,today,geographyMode);if(!next)return;
    setSelectedDate(next.selectedDate);setTodayMode(next.todayMode);setShowRadar(next.showRadar);setRainfall(next.rainfall);setActiveEvidence(next.inspector);
    if(next.inspector==='forecast'){setRightOpen(true);setLeftOpen(false);}
  };
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
  useEffect(()=>{
    const controller=new AbortController();
    const load=()=>fetch('/api/radar',{cache:'no-store',signal:controller.signal}).then(async response=>{if(!response.ok)throw Error();return response.json();}).then((value:RadarSnapshot)=>{
      if(controller.signal.aborted)return;
      if(value.feed?.fetched_at!==radarFeedRef.current){setRadarIndex(Math.max(0,(value.feed?.frames.length??1)-1));radarFeedRef.current=value.feed?.fetched_at??null;}
      setRadarSnapshot(value);
    }).catch(()=>{if(!controller.signal.aborted)setRadarSnapshot({...emptyRadar,error:'Radar snapshot unavailable'});});
    load();const timer=setInterval(load,60000);return()=>{controller.abort();clearInterval(timer);};
  },[refresh]);
  const radarStatus=radarFreshness(radarSnapshot.feed,clock),radarFrame=radarSnapshot.feed?.frames[radarIndex]??null;
  const area=lookup.get(selected)??lookup.get('TH')!;
  const floodViewport=useFloodViewport(showFloods&&floodDisplayMode==='viewport'&&geographyMode!=='basin',floodWindow,area.id,floodSnapshot,floodMapView,refresh);
  useEffect(()=>{rightPanelRef.current?.querySelector<HTMLElement>('[data-inspector-context]')?.scrollTo({top:0,behavior:'auto'});},[area.id,activeEvidence,selectedGauge,selectedRain,selectedDam]);
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
    const mode=showFloods&&floodDisplayMode==='area'?'detail':'summary';
    if(floodSnapshotRef.current.scope?.area_id!==area.id||floodSnapshotRef.current.scope?.mode!==mode||floodSnapshotRef.current.feed?.product_window!==floodWindow||floodGeneration&&floodSnapshotRef.current.pagination?.generation!==floodGeneration)setFloodSnapshot(emptyFloods);
    const load=()=>{setFloodLoading(true);return loadFloodSnapshot(controller.signal,fetch,floodSnapshotRef.current,{areaId:area.id,mode,window:floodWindow,generation:floodGeneration||undefined,page:floodPage})
      .then(value=>{if(active){floodSnapshotRef.current=value;setFloodSnapshot(value);}}).catch(()=>{if(active){
        const previous=floodSnapshotRef.current;
        setFloodSnapshot(previous.feed&&previous.scope?.area_id===area.id&&previous.scope.mode===mode&&previous.feed.product_window===floodWindow&&(!floodGeneration||previous.pagination?.generation===floodGeneration)?{...previous,health:{...previous.health,status:'FAILED'},query_freshness:'DELAYED',error:'GISTDA refresh failed; retaining the previously loaded reference and its original query time.'}:{...emptyFloods,error:'GISTDA selected product is temporarily unavailable'});
      }}).finally(()=>{if(active)setFloodLoading(false);});};
    void load();const timer=setInterval(load,300000);
    return()=>{active=false;controller.abort();clearInterval(timer);};
  },[refresh,area.id,showFloods,geographyMode,floodWindow,floodGeneration,floodPage,floodDisplayMode]);
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
  const mapFloods=useMemo(()=>showFloods?(floodDisplayMode==='viewport'?floodViewport.records:floodsInScope):[],[showFloods,floodDisplayMode,floodViewport.records,floodsInScope]);
  const warningsInScope=useMemo(()=>warningSnapshot.records.filter(r=>warningInArea(r,area,areas)),[warningSnapshot.records,area,areas]);
  const validWarnings=warningsInScope.filter(r=>warningState(r,warningSnapshot.records,clock)==='CURRENT').length;
  const mapWarnings=useMemo(()=>showWarnings?warningMapRecords(warningSnapshot.records,selectedWarning,tmdStatus,clock).filter(r=>warningInArea(r,area,areas)):[],[showWarnings,warningSnapshot.records,selectedWarning,tmdStatus,clock,area,areas]);
  const damsInScope=useMemo(()=>damSnapshot.records.filter(d=>damInArea(d,area)),[damSnapshot.records,area]);
  const availableSources=Number(radarSnapshot.feed!==null)+Number(snapshot.records.length>0)+Number(damSnapshot.records.length>0)+Number(warningSnapshot.feed!==null)+Number(floodSnapshot.feed!==null)+Number(hourlySnapshot.records.length>0)+Number(gaugeSnapshot.feed!==null)+Number(rainSnapshot.feed!==null);
  const dateLabel=date?`${date===bangkokDate(clock)?'Today · ':''}${new Date(date+'T00:00:00+07:00').toLocaleDateString('en-GB',{timeZone:'Asia/Bangkok',day:'2-digit',month:'short',year:'numeric'})}`:'No selected forecast date';
  const recordsById=useMemo(()=>new Map(snapshot.records.map(r=>[r.location_id,r])),[snapshot.records]);
  const current=recordsById.get(area.id);
  const scope=useMemo(()=>snapshot.records.filter(r=>{const a=lookup.get(r.location_id);return a&&contains(area,a);}),[snapshot.records,area,lookup]);
  const dates=dashboardDates(clock);
  const availableDates=new Set(snapshot.records.flatMap(r=>r.valid_periods.map(p=>p.date)));
  const children=areas.filter(a=>geographyMode==='basin'?a.level==='basin':a.level!=='basin'&&a.parent_id===area.id).sort((a,b)=>a.name.localeCompare(b.name));
  const trail:Area[]=[];let parent:Area|undefined=area;while(parent){trail.unshift(parent);parent=parent.parent_id?lookup.get(parent.parent_id):undefined;}
  const select=(id:string)=>{if(!lookup.has(id))return;setSelected(id);if(id.startsWith('TH-B-')){setGeographyMode('basin');setShowWarnings(false);setShowFloods(false);setTodayMode('situation');setSelectedDate(today);}else if(id!=='TH')setGeographyMode('administrative');setSelectedRain(null);setSelectedGauge(null);setSelectedDam(null);setSelectedWarning(null);setSelectedFlood(null);setLeftOpen(false);setRightOpen(true);};
  const selectRain=(id:string|null)=>{setActiveEvidence('thaiwater_rain');setSelectedRain(id);setSelectedGauge(null);setShowRain(true);setRightOpen(true);setLeftOpen(false);};
  const chooseGeography=(value:'administrative'|'basin')=>{setGeographyMode(value);select('TH');setTodayMode('situation');setSelectedDate(today);setLeftOpen(true);setRightOpen(false);if(value==='basin'){setShowWarnings(false);setShowFloods(false);setShowGauges(true);setShowDams(true);setActiveEvidence('thaiwater');}};
  const selectGauge=(id:string|null)=>{setSelectedRain(null);setActiveEvidence('thaiwater');setSelectedGauge(id);setShowGauges(true);setRightOpen(true);setLeftOpen(false);};
  const selectDam=(id:string)=>{setActiveEvidence('rid');setSelectedDam(id);setSelectedWarning(null);setShowDams(true);setRightOpen(true);setLeftOpen(false);};
  const selectWarning=(id:string|null)=>{setActiveEvidence('tmd');setSelectedWarning(id);setSelectedDam(null);setShowWarnings(true);setRightOpen(true);setLeftOpen(false);};
  const selectFlood=(id:string|null)=>{setActiveEvidence('gistda');setSelectedFlood(id);setSelectedWarning(null);setSelectedDam(null);setShowFloods(true);setRightOpen(true);setLeftOpen(false);};
  const oldestFetch=snapshot.records.length?snapshot.records.map(r=>r.fetched_at).sort()[0]:null;
  const firstValid=snapshot.records[0]?.valid_periods[0]?.valid_start;
  function download(){
    const blob=new Blob([JSON.stringify({area:area.id,date,source:'Open-Meteo',records:scope},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`thailand-weather-${area.id}-${date||'unavailable'}.json`;a.click();URL.revokeObjectURL(url);
  }
  const contexts:InspectorId[]=[...(forecastVisible?['forecast' as const]:[]),...(showWarnings?['tmd' as const]:[]),...(showFloods?['gistda' as const]:[]),...(showDams?['rid' as const]:[]),...(showGauges?['thaiwater' as const]:[]),...(showRain?['thaiwater_rain' as const]:[])];
  const context=visibleInspector(activeEvidence,contexts);
  const inspect=(id:InspectorId)=>{setActiveEvidence(id);setRightOpen(true);setLeftOpen(false);};
  const inspectSource=(id:InspectorId)=>{
    if(geographyMode==='basin'&&(id==='tmd'||id==='gistda'))return;
    if(id==='tmd')setShowWarnings(true);if(id==='gistda')setShowFloods(true);if(id==='rid')setShowDams(true);if(id==='thaiwater')setShowGauges(true);if(id==='thaiwater_rain')setShowRain(true);inspect(id);
  };
  const navigate=(id:string)=>{select(id);setActiveEvidence(forecastVisible?'forecast':'area');};
  const navigateHierarchy=(id:string)=>{navigate(id);if(window.matchMedia('(min-width:901px)').matches){setLeftOpen(true);setRightOpen(false);}};
  const openControls=(tab:'layers'|'geography')=>{setControlsTab(tab);setLeftOpen(true);setRightOpen(false);};
  const layers:LayerOption[]=[
    {id:'TMD warnings',label:'Official CAP warnings',detail:'TMD · validity and geometry qualified',checked:showWarnings,disabled:geographyMode==='basin',icon:<Radio size={16}/>,onChange:value=>{setShowWarnings(value);setSelectedWarning(null);}},
    {id:'GISTDA flood footprints',label:'Flood footprints · retrospective',detail:'GISTDA · separate 3 / 7 / 30-day queries',checked:showFloods,disabled:geographyMode==='basin',icon:<Satellite size={16}/>,onChange:value=>{setShowFloods(value);setSelectedFlood(null);}},
    {id:'RID dams',label:'Reservoir storage',detail:'RID · daily report, original units',checked:showDams,disabled:false,icon:<Database size={16}/>,onChange:value=>{setShowDams(value);setSelectedDam(null);}},
    {id:'HII water stations',label:'River level stations',detail:'HII · observation timezone unknown',checked:showGauges,disabled:false,icon:<Waves size={16}/>,onChange:value=>{setShowGauges(value);setSelectedGauge(null);}},
    {id:'HII rain stations',label:'Observed rain stations',detail:'HII · point observations, mm/24h and mm/1h',checked:showRain,disabled:false,icon:<Droplets size={16}/>,onChange:value=>{setShowRain(value);setSelectedRain(null);}},
  ];
  const mapEvidence:MapLegendEntry[]=[];
  if(showRadar)mapEvidence.push({kind:'radar',status:`${radarStatus} · ${radarLoad?.status??'not loaded'} · ${bangkokTime(radarFrame?.observed_at)}`,onInspect:()=>document.getElementById('radar-time')?.focus(),detail:`TMD composite · ${radarStatus} · frame ${bangkokTime(radarFrame?.observed_at)} · UTC source time · mm/hour estimate · blank pixels do not establish no rain`});
  if(showGauges)mapEvidence.push({kind:'water',status:`${gaugeStatus} query · obs time unknown`,onInspect:()=>inspect('thaiwater'),detail:`HII / ThaiWater · checked ${bangkokTime(gaugeSnapshot.feed?.fetched_at)} · ${gaugeStatus} query · ม.รทก. ไม่ใช่ความลึกน้ำท่วม · observation timezone / age unknown`});
  if(showRain)mapEvidence.push({kind:'rain',status:`${rainStatus} query · obs time unknown`,onInspect:()=>inspect('thaiwater_rain'),detail:`HII / ThaiWater · checked ${bangkokTime(rainSnapshot.feed?.fetched_at)} · ${rainStatus} query · mm/24h และ mm/1h ตามสถานี ไม่ใช่ค่าเฉลี่ยพื้นที่ · observation timezone / age unknown`});
  if(showDams)mapEvidence.push({kind:'dam',status:`${ridStatus} · ${damSnapshot.records[0]?.report_date??'no report'}`,onInspect:()=>inspect('rid'),detail:`RID daily storage · ${reportDate(damSnapshot.records[0]?.report_date)} · ${ridStatus} · วงแสดง % ปริมาตรเทียบความจุปกติ (+ คือเกิน 100%, ? คือไม่ระบุ) · สีเทาเมื่อเวลาไม่สด/ไม่ยืนยัน · ไม่ใช่ระดับน้ำหรือเกณฑ์อันตราย · เลือกจากรายการเพื่อซูมจุดที่อยู่ใกล้กัน`});
  if(showWarnings)mapEvidence.push({kind:'warning',status:`${tmdStatus} · ${validWarnings} current · ${warningSnapshot.records.filter(r=>r.geometry_issues?.length).length} geometry qualified`,onInspect:()=>inspect('tmd'),detail:`TMD CAP · ${selectedWarning&&mapWarnings.some(r=>r.display_state!=='CURRENT')?'PREVIOUS / NON-CURRENT MESSAGE':`${validWarnings} within validity window · ${tmdStatus}`} · checked ${bangkokTime(warningSnapshot.feed?.fetched_at)} · สีตามประกาศ สีเทาเป็นข้อมูลอ้างอิงที่ไม่ใช่คำเตือนปัจจุบัน`});
  if(showFloods)mapEvidence.push({kind:'flood',status:`${floodWindow} · ${gistdaStatus} query · ${floodDisplayMode==='viewport'?floodViewport.status:floodSnapshot.presentation??'loading'} · acquisition unknown`,onInspect:()=>inspect('gistda'),detail:`GISTDA · ${floodWindowText(floodSnapshot.feed?.product_window??floodWindow)} · ${floodScope} · ${floodInScope?`${floodResultCount(floodSnapshot,area)??'—'} returned features`:'outside selected area'} · displaying ${mapFloods.length} footprints · ${floodDisplayMode==='viewport'?viewportStatusText(floodViewport.status,mapFloods.length,floodViewport.matched_count)+' · ':floodSnapshot.presentation==='page'?'one selected page · ':''}checked ${bangkokTime(floodSnapshot.feed?.fetched_at)} · ${gistdaStatus} query · acquisition time/current flood state unknown`});
  if(now===null)return <main className="dashboard"><p>Preparing Thailand situation view…</p></main>;
  return <main className={`dashboard ${styles.shell}`}>
    <a href="#area-navigation" className="skip-link" onClick={()=>openControls('geography')}>Skip map to area navigation</a>
    <WorkspaceTopbar areas={areas} available={availableSources} total={8} onSelect={navigate} onSources={openSources} onSummary={()=>setOverviewOpen(true)} onCompare={()=>setProvincesOpen(true)}/>
    <section className="map-workspace" aria-label="Thailand map workspace">
      <div className="workspace-bar"><nav aria-label="Selected geography">{trail.map((a,i)=><span key={a.id}>{i>0&&<ChevronRight size={12}/>}<button onClick={()=>navigate(a.id)}>{a.name}</button></span>)}</nav><div className={styles.contextTools}>
        <span className={styles.modeTag}>{background==='radar'?'Observed radar':mode==='situation'?'Situation monitoring':`${mode==='hourly'?'Hourly':'Daily'} forecast`} · {dateLabel}</span>
        <span className={styles.themeClock}>{theme} · {new Date(clock).toLocaleTimeString('en-GB',{timeZone:'Asia/Bangkok',hour:'2-digit',minute:'2-digit'})} ICT</span>
        <div className="dimension-toggle"><button aria-pressed={!is3d} className={!is3d?'active':''} onClick={()=>setIs3d(false)}>2D</button><button aria-pressed={is3d} className={is3d?'active':''} onClick={()=>setIs3d(true)}>3D</button></div>
        <button className="mobile-panel-button" onClick={()=>openControls('layers')}><Layers3 size={14}/>Layers</button><button className="mobile-panel-button" onClick={()=>{setLeftOpen(false);setRightOpen(true);}}><Info size={14}/>Area</button>
      </div></div>
      {geographyMode==='basin'&&<p className={styles.basinNote}>22 DDPM basins · point-matched station and dam context. No inferred upstream/downstream network or basin forecast fill.</p>}
      <MapLegend entries={mapEvidence}/>
      <div className="workspace-body">
        <WorkspaceRail leftOpen={leftOpen} tab={controlsTab} inspectorOpen={rightOpen} onPanel={openControls} onInspector={()=>{setRightOpen(!rightOpen);setLeftOpen(false);}}/>
        <LayerControls open={leftOpen} tab={controlsTab} onTab={setControlsTab} onClose={()=>setLeftOpen(false)} layers={layers} forecastVisible={forecastVisible} opacity={opacity} onOpacity={setOpacity} terrain={terrain} onTerrain={setTerrain} extrude={extrude} onExtrude={setExtrude} canExtrude={forecastVisible&&['province','district'].includes(area.level)} area={area} children={children} geography={geographyMode} onGeography={chooseGeography} onArea={navigateHierarchy}/>
        <div className="map-column"><MapView onViewportChange={setFloodMapView} radarFrame={showRadar&&radarVisible(radarStatus)?radarFrame:null} radarOpacity={radarOpacity} onRadarLoad={setRadarLoad} geographyMode={geographyMode} area={area} areas={areas} records={snapshot.records} gauges={mapStationRows} showGauges={showGauges||showRain} selectedGauge={selectedRain??selectedGauge} onSelectGauge={id=>id.startsWith('THR-')?selectRain(id):selectGauge(id)} dams={damsInScope} showDams={showDams} damFreshness={ridStatus} selectedDam={selectedDam} onSelectDam={selectDam} warnings={mapWarnings} onSelectWarning={selectWarning} floods={mapFloods} floodFreshness={gistdaStatus} floodWindow={floodWindow} floodHistorical={floodWindow!=='3days'||!!floodSnapshot.historical_query} selectedFlood={selectedFlood} onSelectFlood={selectFlood} date={date} metric={metric} is3d={is3d} terrain={terrain} theme={theme} hourly={mode==='hourly'?{records:hourlySnapshot.records,validEnd:activeHour?.valid_end??''}:null} validTimeLabel={mode==='hourly'?(activeHour?hourLabel(activeHour):'No hourly interval available'):`${date} · ICT 00:00–24:00`} rainfall={forecastVisible} extrude={extrude} opacity={opacity} freshness={displayStatus} onSelect={navigate}/>
          {forecastVisible&&<div className="legend"><div><b>{metricLabel(metric)}</b><span>{metricUnit(metric,mode==='hourly'?'hourly':'daily')} · representative point</span></div><div className="legend-scale">{(metric==='rainfall_mm'?(mode==='hourly'?[0,.2,1,5,10]:[0,1,10,25,50]):[0,20,40,60,80]).map(v=><span key={v}><i style={{background:`rgba(${metricColor(v,metric,mode==='hourly'?'hourly':'daily').slice(0,3).join(',')},1)`}}/>{v}{v===(metric==='rainfall_mm'?(mode==='hourly'?10:50):80)?'+':''}</span>)}<span><i className="no-data"/>No data / stale</span></div></div>}
        </div>
        <ContextInspector open={rightOpen} context={context} contexts={contexts} onContext={setActiveEvidence} onClose={()=>{setRightOpen(false);document.querySelector<HTMLButtonElement>('button[aria-label="Toggle inspector"]')?.focus();}} panelRef={rightPanelRef}>
          {context==='area'&&<AreaInspector area={area} onSource={inspectSource} sources={[
            {id:'tmd',title:'TMD official CAP warnings',detail:`${tmdStatus} · ${validWarnings} within validity window`,disabled:geographyMode==='basin'},
            {id:'gistda',title:'GISTDA flood footprints',detail:`${floodWindow} retrospective · ${gistdaStatus} query · acquisition unknown`,disabled:geographyMode==='basin'},
            {id:'rid',title:'RID reported storage',detail:`${ridStatus} · report ${damSnapshot.records[0]?.report_date??'unavailable'}`},
            {id:'thaiwater',title:'HII river level stations',detail:`${gaugeStatus} query · observation timezone unknown`},
            {id:'thaiwater_rain',title:'HII observed rain stations',detail:`${rainStatus} query · observation timezone unknown`},
          ]}/>}
          {context==='forecast'&&(mode==='hourly'?<HourlyPanel showSelector={false} loading={hourlyLoading} area={area} snapshot={hourlySnapshot} now={clock} selectedEnd={activeHour?.valid_end??''} onHour={setSelectedHour}/>:<ForecastInspector area={area} current={current} date={date} scopeCount={scope.length} status={status} oldestFetch={oldestFetch} firstValid={firstValid} loading={loading} failed={snapshot.status?.status==='FAILED'} onExport={scope.length&&geographyMode!=='basin'?download:undefined}/>)}
          {context==='tmd'&&<WarningPanel area={area} areas={areas} snapshot={warningSnapshot} freshness={tmdStatus} selectedId={selectedWarning} now={clock} onSelect={selectWarning}/>}
          {context==='gistda'&&<FloodPanel key={`gistda:${area.id}:${floodWindow}:${floodGeneration}`} area={area} snapshot={floodSnapshot} queryFreshness={gistdaStatus} selectedId={selectedFlood} onSelect={selectFlood} onArea={select}
                window={floodWindow} onWindow={value=>{setFloodWindow(value);setFloodGeneration('');setFloodPage(0);setSelectedFlood(null);setFloodSnapshot({...emptyFloods,window_catalog:floodSnapshot.window_catalog});}}
                generation={floodGeneration} onGeneration={value=>{setFloodGeneration(value);setFloodPage(0);setSelectedFlood(null);setFloodSnapshot({...emptyFloods,window_catalog:floodSnapshot.window_catalog,query_history:floodSnapshot.query_history});}}
                onPage={value=>{setFloodPage(value);setSelectedFlood(null);}} displayMode={floodDisplayMode} viewport={floodViewport}
                onDisplayMode={value=>{setFloodDisplayMode(value);setFloodPage(0);setSelectedFlood(null);}}/>}
          {context==='rid'&&<DamPanel area={area} snapshot={damSnapshot} freshness={ridStatus} selectedId={selectedDam} onSelect={selectDam} onClose={()=>setSelectedDam(null)}/>}
          {context==='thaiwater'&&<GaugePanel key={area.id} area={area} snapshot={gaugeSnapshot} queryFreshness={gaugeStatus} selectedId={selectedGauge} loading={gaugeLoading} onSelect={selectGauge}/>}
          {context==='thaiwater_rain'&&<RainPanel key={area.id} area={area} snapshot={rainSnapshot} freshness={rainStatus} selectedId={selectedRain} onSelect={selectRain}/>}
        </ContextInspector>
      </div>
      <TimeDock dates={dates} date={date} today={today} available={availableDates} geography={geographyMode} onDate={setDate} background={background} onBackground={chooseBackground} metric={metric} onMetric={setMetric} forecastVisible={forecastVisible} unit={displayUnit} hours={hours} selectedHour={activeHour?.valid_end??''} onHour={setSelectedHour} loading={loading} onRefresh={()=>setRefresh(x=>x+1)} radar={showRadar?<RadarPlayer snapshot={radarSnapshot} index={radarIndex} onIndex={setRadarIndex} opacity={radarOpacity} onOpacity={setRadarOpacity} load={radarLoad} now={clock}/>:undefined}/>
    </section>
    <div className="bottomline"><span>{snapshot.storage==='local'?'LOCAL PREVIEW · stored source snapshots':snapshot.storage==='mongo'?'Published source snapshots · independent clocks':'Data connection pending'}{snapshot.error?` · ${snapshot.error}`:''}</span><span>Missing data never establishes safety · <Link href="/methodology">Methodology</Link></span></div>
    {overviewOpen&&<WorkspaceDialog title="Situation overview" onClose={()=>setOverviewOpen(false)}><SituationOverview items={[
      {title:'TMD official warnings',disabled:geographyMode==='basin',value:warningSnapshot.records.filter(r=>warningState(r,warningSnapshot.records,clock)==='CURRENT').length,unit:'national feed messages within validity window',detail:`${tmdStatus} · not an affected-area count`,onInspect:()=>{setOverviewOpen(false);inspectSource('tmd');}},
      {title:'HII rain observations',value:rainSnapshot.feed?.record_count??'—',unit:'returned rain-station records',detail:`${rainStatus} query · observation age unknown`,onInspect:()=>{setOverviewOpen(false);inspectSource('thaiwater_rain');}},
      {title:'RID reservoir storage',value:damSnapshot.records.length,unit:'published dam reports',detail:`${ridStatus} · report ${damSnapshot.records[0]?.report_date??'unavailable'}`,onInspect:()=>{setOverviewOpen(false);inspectSource('rid');}},
      {title:'GISTDA retrospective product',disabled:geographyMode==='basin',value:floodSnapshot.feed?.record_count??'—',unit:`national returned features · ${floodWindow}`,detail:`${gistdaStatus} query · acquisition/current flood state unknown`,onInspect:()=>{setOverviewOpen(false);inspectSource('gistda');}},
    ]}/></WorkspaceDialog>}
    {provincesOpen&&<WorkspaceDialog title="Compare 77 provinces" onClose={()=>setProvincesOpen(false)}><ProvinceOverview onSelect={id=>{setProvincesOpen(false);navigate(id);}} onClose={()=>setProvincesOpen(false)}/></WorkspaceDialog>}
    {sourcesOpen&&<div className="modal-backdrop" onClick={()=>setSourcesOpen(false)}><section className="sources-modal" role="dialog" aria-modal="true" aria-label="Source status" onClick={e=>e.stopPropagation()}><div className="modal-heading"><div><p className="eyebrow">PROVENANCE & AVAILABILITY</p><h2>Independent sources. Clear timestamps.</h2></div><button autoFocus aria-label="Close source status" onClick={()=>setSourcesOpen(false)}><X size={20}/></button></div><p className="modal-intro">Missing data is unavailable, never an indication of normal or safe conditions. Sources update independently.</p>{(registry as Source[]).map(source=><article className="source-row" key={source.id}><div><h3>{source.organization}<span className="mini-tag">{source.state.replaceAll('_',' ')}</span></h3><p>{source.name} · {source.id==='open_meteo'?(snapshot.records.length?`${status} · ${snapshot.records.length} points`: 'UNAVAILABLE'):source.id==='open_meteo_hourly'?(hourlyChecked?`${hourlyStatus} · ${hourlySnapshot.records.length} points`:'Not checked · open Today hourly'):source.id==='thaiwater_rain'?(rainSnapshot.feed?`${rainStatus} query · ${rainSnapshot.feed.record_count} rain stations · observation age unknown`:'UNAVAILABLE'):source.id==='thaiwater'?(gaugeSnapshot.feed?`${gaugeStatus} query · ${gaugeSnapshot.feed.record_count} stations · observation age unknown`:'UNAVAILABLE'):source.id==='rid'?`${ridStatus} · ${damSnapshot.records.length} reports`:source.id==='tmd'?`${tmdStatus} · ${warningSnapshot.records.length} latest-feed messages`:source.id==='gistda'?(floodSnapshot.feed?`${gistdaStatus} query · ${floodResultCount(floodSnapshot,area)??"—"} returned · ${floodScope}`:'UNAVAILABLE'):source.status}</p><small>{source.description}</small><div className="source-meta"><span>{source.cadence}</span><span>{source.id==='open_meteo'?`Retrieved ${bangkokTime(oldestFetch)}`:source.id==='open_meteo_hourly'?`Hourly retrieved ${bangkokTime(hourlySnapshot.records[0]?.fetched_at)}`:source.id==='thaiwater_rain'?`Rain response ${bangkokTime(rainSnapshot.feed?.fetched_at)} · observation timezone unknown`:source.id==='thaiwater'?`Station response ${bangkokTime(gaugeSnapshot.feed?.fetched_at)} · observation timezone unknown`:source.id==='rid'?(damSnapshot.records.length?`Report ${reportDate(damSnapshot.records[0].report_date)}`:'Awaiting published report'):source.id==='tmd'?`Feed checked ${bangkokTime(warningSnapshot.feed?.fetched_at)}`:source.id==='gistda'?`Query checked ${bangkokTime(floodSnapshot.feed?.fetched_at)} · acquisition unknown`:'Acceptance pending'}</span></div><a href={source.url} target="_blank" rel="noreferrer">Source documentation <ArrowUpRight size={12}/></a></div></article>)}<Link className="registry-link" href="/health">Data health · สุขภาพระบบข้อมูล <ArrowUpRight size={14}/></Link><Link className="registry-link" href="/sources">Full source registry & terms <ArrowUpRight size={14}/></Link></section></div>}
  </main>;
}
