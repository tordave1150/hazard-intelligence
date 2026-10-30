import 'server-only';
import cores from '@/data/basin-membership-cores.json';
import type {Geometry} from 'geojson';
import {geometryContains} from './basin-geometry';
export function basinForPoint(point:{lat:number;lon:number}|null):string|null{
  if(!point)return null;
  const hits=cores.features.filter(f=>{
    const [west,south,east,north]=f.properties.bbox;
    return point.lon>west&&point.lon<east&&point.lat>south&&point.lat<north&&geometryContains(f.geometry as Geometry,point);
  });
  return hits.length===1?hits[0].properties.id:null;
}
export function withBasin<T extends {point:{lat:number;lon:number}|null}>(row:T){
  const basin_id=basinForPoint(row.point);
  return {...row,basin_id,basin_assignment:basin_id?'CONFIRMED_INTERIOR_POINT' as const:'UNCONFIRMED' as const};
}
