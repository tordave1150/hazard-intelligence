import type {Geometry} from 'geojson';
function ringContains(ring:number[][],x:number,y:number){
  let inside=false;
  for(let i=0,j=ring.length-1;i<ring.length;j=i++){
    const [xi,yi]=ring[i],[xj,yj]=ring[j];
    if((yi>y)!==(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi)inside=!inside;
  }
  return inside;
}
export function geometryContains(geometry:Geometry,point:{lat:number;lon:number}){
  if(!Number.isFinite(point.lat)||!Number.isFinite(point.lon))return false;
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.type==='MultiPolygon'?geometry.coordinates:[];
  return polygons.some(rings=>ringContains(rings[0],point.lon,point.lat)&&!rings.slice(1).some(r=>ringContains(r,point.lon,point.lat)));
}
