'use client';
import {useEffect,useRef,useState} from 'react';
import maplibregl,{type Map as MapType} from 'maplibre-gl';
import {MapboxOverlay} from '@deck.gl/mapbox';
import {GeoJsonLayer} from '@deck.gl/layers';
import type {Feature,FeatureCollection,Geometry} from 'geojson';
import type {Area,DamObservation,Forecast,Freshness,Metric} from '@/lib/types';
import {metricColor,metricValue,metricUnit} from '@/lib/semantics';
import {LocateFixed,Plus,Minus,Map as MapIcon} from 'lucide-react';

type Props={area:Area;areas:Area[];records:Forecast[];date:string;metric:Metric;is3d:boolean;terrain:boolean;
  rainfall:boolean;extrude:boolean;opacity:number;freshness:Freshness;onSelect:(id:string)=>void;
  dams:DamObservation[];showDams:boolean;damFreshness:Freshness;selectedDam:string|null;onSelectDam:(id:string)=>void};
export default function MapView(props:Props){
  const stale=['STALE','UNKNOWN','UNAVAILABLE'].includes(props.freshness);
  const container=useRef<HTMLDivElement>(null),map=useRef<MapType|null>(null),overlay=useRef<MapboxOverlay|null>(null);
  const hoverPopup=useRef<maplibregl.Popup|null>(null);
  const latest=useRef(props);latest.current=props;
  const [ready,setReady]=useState(false),[error,setError]=useState(''),[baseError,setBaseError]=useState(false);
  const [geometry,setGeometry]=useState<FeatureCollection>({type:'FeatureCollection',features:[]});
  useEffect(()=>{
    if(!container.current)return;
    let instance:MapType;
    try {
      instance=new maplibregl.Map({container:container.current,style:'https://tiles.openfreemap.org/styles/positron',
        center:[101.05,13.1],zoom:4.65,minZoom:3,maxZoom:16,maxPitch:70,
        attributionControl:false,bounds:[[97.1,5.4],[105.8,20.7]],fitBoundsOptions:{padding:35}});
      map.current=instance;
      instance.addControl(new maplibregl.AttributionControl({compact:true,customAttribution:
        '<a href="https://github.com/chingchai/OpenGISData-Thailand">Boundaries: OpenGISData-Thailand</a> · CC BY 4.0 (simplified)'}),'bottom-right');
      const fallback=setTimeout(()=>{
        if(!instance.isStyleLoaded()){
          setBaseError(true);instance.setStyle({version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#e3ecea'}}]});
        }
      },12000);
      instance.once('load',()=>{
        clearTimeout(fallback);
        const deck=new MapboxOverlay({interleaved:true,layers:[]});
        overlay.current=deck;
        instance.addControl(deck);
        instance.addSource('terrain-dem',{type:'raster-dem',url:'https://tiles.mapterhorn.com/tilejson.json',tileSize:512,
          attribution:'<a href="https://mapterhorn.com/attribution/">Elevation: Mapterhorn & sources</a>'});
        instance.addSource('weather-native',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
        const label=instance.getStyle().layers.find(layer=>layer.type==='symbol')?.id;
        instance.addLayer({id:'weather-native-fill',type:'fill',source:'weather-native',layout:{visibility:'none'},
          paint:{'fill-color':['get','color'],'fill-opacity':.6}},label);
        instance.addLayer({id:'weather-native-line',type:'line',source:'weather-native',layout:{visibility:'none'},
          paint:{'line-color':'#597e7b','line-width':1}},label);
        instance.addLayer({id:'weather-native-extrusion',type:'fill-extrusion',source:'weather-native',layout:{visibility:'none'},
          paint:{'fill-extrusion-color':['get','color'],'fill-extrusion-height':['get','height'],'fill-extrusion-base':0,'fill-extrusion-opacity':.65}});
        const popup=new maplibregl.Popup({closeButton:false,closeOnClick:false});
        hoverPopup.current=popup;
        instance.on('mousemove',event=>{
          if(!latest.current.is3d){popup.remove();return;}
          const feature=instance.queryRenderedFeatures(event.point,{layers:['weather-native-fill','weather-native-extrusion']})[0];
          instance.getCanvas().style.cursor=feature?'pointer':'';
          if(feature?.properties){const p=feature.properties;
            popup.setLngLat(event.lngLat).setText(`${p.name} · Open-Meteo forecast · ${latest.current.date} ICT · ${p.value==null?'No current value':`${p.value} ${metricUnit(latest.current.metric)}`} · Representative point, not area average`).addTo(instance);
          } else popup.remove();
        });
        instance.on('click',event=>{
          if(!latest.current.is3d)return;
          const feature=instance.queryRenderedFeatures(event.point,{layers:['weather-native-fill','weather-native-extrusion']})[0];
          if(feature?.properties)latest.current.onSelect(latest.current.area.level==='national'?feature.properties.region_id:feature.properties.id);
        });
        setReady(true);
      });
      instance.on('error',event=>{
        const message=event.error?.message??'';
        if(message.includes('WebGL'))setError('This device could not initialize WebGL. Use the area controls to explore the same data.');
        else if(message.includes('terrain')||message.includes('mapterhorn'))setError('Terrain tiles are unavailable; flat geography remains available.');
      });
      instance.on('webglcontextlost',()=>setError('Map graphics were interrupted. Reload to restore the map; area data remains available.'));
      return ()=>{clearTimeout(fallback);overlay.current=null;instance.remove();map.current=null;};
    } catch {setError('WebGL is unavailable on this device. Area search, navigation and forecasts remain available.');}
  },[]);
  useEffect(()=>{
    const controller=new AbortController();
    setGeometry({type:'FeatureCollection',features:[]});
    const url=props.area.level==='province'||props.area.level==='district' ? `/data/districts/${props.area.province_id}.geojson`:'/data/provinces.geojson';
    fetch(url,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{
      const features=(data as FeatureCollection).features.filter(f=>props.area.level!=='region'||f.properties?.region_id===props.area.id);
      setGeometry({type:'FeatureCollection',features});
    }).catch(e=>{if(e.name!=='AbortError'){setGeometry({type:'FeatureCollection',features:[]});setError('Boundary data is unavailable.');}});
    return ()=>controller.abort();
  },[props.area.id,props.area.level,props.area.province_id]);
  useEffect(()=>{hoverPopup.current?.remove();},[props.area.id,props.is3d,props.metric,props.date]);
  useEffect(()=>{
    if(!ready||!map.current||!props.showDams)return;
    const instance=map.current;
    let markers:maplibregl.Marker[]=[];
    const makeDamMarker=(dam:DamObservation)=>{
      const button=document.createElement('button');
      button.type='button';button.className='dam-marker';button.textContent='◆';
      button.dataset.stale=String(!['FRESH','DELAYED'].includes(props.damFreshness));
      button.setAttribute('aria-label',`${dam.name_th}, RID report ${dam.report_date}, ${dam.storage_pct===null?'percentage unavailable':dam.storage_pct.toFixed(2)+'% of normal capacity'}`);
      button.dataset.damId=dam.dam_id;
      button.setAttribute('aria-pressed',String(latest.current.selectedDam===dam.dam_id));
      const show=()=>{hoverPopup.current?.setLngLat([dam.point.lon,dam.point.lat]).setText(`${dam.name_th} · RID daily report ${dam.report_date} · ${dam.storage_pct===null?'No percentage':dam.storage_pct.toFixed(2)+'% of normal capacity'}`).addTo(map.current!);};
      button.addEventListener('mouseenter',show);button.addEventListener('focus',show);
      button.addEventListener('mouseleave',()=>hoverPopup.current?.remove());button.addEventListener('blur',()=>hoverPopup.current?.remove());
      button.addEventListener('click',event=>{event.stopPropagation();hoverPopup.current?.remove();latest.current.onSelectDam(dam.dam_id);});
      return new maplibregl.Marker({element:button,anchor:'center'}).setLngLat([dam.point.lon,dam.point.lat]).addTo(instance);
    };
    const draw=()=>{
      markers.forEach(marker=>marker.remove());
      if(props.area.level==='national'&&instance.getZoom()<6){
        const groups=new Map<string,DamObservation[]>();
        for(const dam of props.dams)groups.set(dam.region_id,[...(groups.get(dam.region_id)??[]),dam]);
        markers=[...groups].map(([region,rows])=>{
          if(rows.length===1)return makeDamMarker(rows[0]);
          const name=props.areas.find(a=>a.id===region)?.name??region;
          const center:[number,number]=[rows.reduce((sum,d)=>sum+d.point.lon,0)/rows.length,rows.reduce((sum,d)=>sum+d.point.lat,0)/rows.length];
          const button=document.createElement('button');button.type='button';button.className='dam-marker dam-cluster';button.textContent=String(rows.length);
          button.dataset.stale=String(!['FRESH','DELAYED'].includes(props.damFreshness));
          button.setAttribute('aria-label',`Explore ${rows.length} RID reservoirs in ${name}`);
          button.title=`${rows.length} RID reservoir reports · ${name}`;
          button.addEventListener('click',event=>{event.stopPropagation();hoverPopup.current?.remove();latest.current.onSelect(region);});
          return new maplibregl.Marker({element:button,anchor:'center'}).setLngLat(center).addTo(instance);
        });
      }else markers=props.dams.map(makeDamMarker);
    };
    draw();instance.on('zoomend',draw);
    return()=>{instance.off('zoomend',draw);hoverPopup.current?.remove();markers.forEach(marker=>marker.remove());};
  },[ready,props.dams,props.showDams,props.damFreshness,props.area.level,props.areas]);
  useEffect(()=>{
    container.current?.querySelectorAll<HTMLButtonElement>('[data-dam-id]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.damId===props.selectedDam)));
  },[props.selectedDam,props.dams,props.showDams,ready]);
  useEffect(()=>{
    if(!ready||!map.current)return;
    map.current.fitBounds(props.area.bbox,{padding:props.area.level==='national'?35:55,maxZoom:props.area.level==='district'?11:9,duration:650,
      pitch:props.is3d?52:0,bearing:props.is3d?-12:0});
  },[props.area.id,props.is3d,ready]);
  useEffect(()=>{
    if(!ready||!map.current)return;
    map.current.setTerrain(props.is3d&&props.terrain?{source:'terrain-dem',exaggeration:1.2}:null);
  },[props.is3d,props.terrain,ready]);
  useEffect(()=>{
    if(!ready||!overlay.current)return;
    const lookup=new Map(props.records.map(r=>[r.location_id,r]));
    const features=geometry.features.map(f=>({...f,properties:{...f.properties,
      value:stale?null:metricValue(lookup.get(f.properties?.id),props.date,props.metric)}}));
    const extrusion=props.is3d&&props.extrude&&['province','district'].includes(props.area.level)&&props.rainfall&&!stale;
    const native=map.current?.getSource('weather-native') as maplibregl.GeoJSONSource|undefined;
    native?.setData({type:'FeatureCollection',features:features.map(f=>{
      const color=props.rainfall?metricColor(f.properties.value,props.metric):[228,236,232,190];
      return {...f,properties:{...f.properties,color:`rgb(${color.slice(0,3).join(',')})`,height:extrusion&&f.properties.value!=null?f.properties.value*(props.metric==='rainfall_mm'?150:50):0}};
    })});
    for(const id of ['weather-native-fill','weather-native-line','weather-native-extrusion']){
      map.current?.setLayoutProperty(id,'visibility',props.is3d&&(id!=='weather-native-extrusion'||extrusion)?'visible':'none');
    }
    map.current?.setPaintProperty('weather-native-fill','fill-opacity',props.opacity/100*.75);
    map.current?.setPaintProperty('weather-native-extrusion','fill-extrusion-opacity',props.opacity/100);
    // MapLibre drapes its own fill/extrusion geometry on DEM terrain. The deck
    // layer handles 2D, where a flat z=0 mesh cannot be buried below terrain.
    overlay.current.setProps({layers:props.is3d?[]:[new GeoJsonLayer({id:'weather-geography',data:{type:'FeatureCollection',features} as FeatureCollection,
      pickable:true,filled:true,stroked:true,extruded:extrusion,
      getFillColor:(f:Feature)=>props.rainfall?metricColor(f.properties?.value??null,props.metric):[228,236,232,190],
      getLineColor:(f:Feature)=>f.properties?.id===props.area.id?[9,100,109,255]:[94,121,121,170],
      getLineWidth:(f:Feature)=>f.properties?.id===props.area.id?2.5:0.8,lineWidthUnits:'pixels',lineWidthMinPixels:.6,
      getElevation:(f:Feature)=>extrusion&&f.properties?.value!=null?f.properties.value*(props.metric==='rainfall_mm'?150:50):0,
      opacity:props.opacity/100,autoHighlight:true,highlightColor:[38,156,156,65],
      onHover:({object})=>{if(map.current)map.current.getCanvas().style.cursor=object?'pointer':'';},
      onClick:({object})=>{
        if(!object)return;
        const id=object.properties.id;
        latest.current.onSelect(latest.current.area.level==='national'?object.properties.region_id:id);
      }
    })],getTooltip:({object})=>object?{text:`${object.properties.name}\n${object.properties.name_th}\n${object.properties.value==null?'No current display value':`${Number(object.properties.value).toFixed(1)} ${metricUnit(props.metric)} · forecast`}\nOpen-Meteo · ${props.date} · ICT 00:00–24:00\nRepresentative point, not an area average`,style:{background:'#153f48',color:'#fff',fontSize:'12px',borderRadius:'8px',padding:'10px'}}:null});
  },[ready,geometry,props.records,props.date,props.metric,props.area,props.is3d,props.rainfall,props.extrude,props.opacity,stale]);
  return <div className="map-shell" aria-label="Thailand situation map">
    <div ref={container} className="map-canvas"/>
    <div className="map-context"><span className="map-context-icon"><MapIcon size={15}/></span><div><strong>{props.area.level==='national'?'Thailand · national view':props.area.name}</strong><span>{props.area.level==='national'?'Select a region to explore':'Select an area for local intelligence'}</span></div></div>
    <div className="map-actions"><button title="Zoom in" aria-label="Zoom in" onClick={()=>map.current?.zoomIn()}><Plus size={18}/></button><button title="Zoom out" aria-label="Zoom out" onClick={()=>map.current?.zoomOut()}><Minus size={18}/></button><button title="Fit selected area" aria-label="Fit selected area" onClick={()=>map.current?.fitBounds(props.area.bbox,{padding:40})}><LocateFixed size={18}/></button></div>
    {(error||baseError)&&<div className="map-error" role="status">{error||'Basemap connection unavailable · local boundary view'}</div>}
    <div className="map-caption">{!props.rainfall?'Administrative geography':props.freshness==='UNAVAILABLE'?'Weather snapshot unavailable':props.freshness==='UNKNOWN'?'Snapshot timing unknown · thematic colors paused':stale?'Stale snapshot · thematic colors paused':'Open-Meteo · model forecast'}<span>{props.is3d?'3D view':'2D view'}</span></div>
  </div>;
}
