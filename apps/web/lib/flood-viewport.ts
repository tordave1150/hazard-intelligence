import type {FloodFeature,FloodWindow} from './types';
export type FloodBounds=[number,number,number,number];
export type FloodMapView={bbox:FloodBounds;zoom:number;settled:boolean};
export type FloodViewport={generation:string;window:FloodWindow;area_id:string;bbox:FloodBounds;fetched_at:string;source_record_count:number;
  status:'AVAILABLE'|'PARTIAL'|'EMPTY'|'ZOOM_REQUIRED'|'INDEX_UNAVAILABLE'|'GEOMETRY_UNAVAILABLE';records:FloodFeature[];
  matched_count:number|null;complete:boolean;reason:string;index_chunks:number;geometry_chunks:number};
export const viewportFeatureLimit=2000,viewportByteLimit=4*1024*1024;
export function validFloodBounds(value:unknown):value is FloodBounds{
  return Array.isArray(value)&&value.length===4&&value.every(v=>typeof v==='number'&&Number.isFinite(v))&&
    value[0]>=-180&&value[2]<=180&&value[1]>=-90&&value[3]<=90&&value[0]<=value[2]&&value[1]<=value[3];
}
export const boundsIntersect=(a:FloodBounds,b:FloodBounds)=>a[0]<=b[2]&&a[2]>=b[0]&&a[1]<=b[3]&&a[3]>=b[1];
export function unionBounds(boxes:FloodBounds[]):FloodBounds{
  const result:FloodBounds=[180,90,-180,-90];for(const b of boxes){result[0]=Math.min(result[0],b[0]);result[1]=Math.min(result[1],b[1]);result[2]=Math.max(result[2],b[2]);result[3]=Math.max(result[3],b[3]);}return result;
}
export function floodFeatureBounds(row:FloodFeature):FloodBounds{
  const result:FloodBounds=[180,90,-180,-90],stack:unknown[]=[row.geometry.coordinates];
  while(stack.length){const value=stack.pop() as unknown[];if(typeof value[0]==='number'){
    const x=value[0],y=value[1] as number;result[0]=Math.min(result[0],x);result[1]=Math.min(result[1],y);result[2]=Math.max(result[2],x);result[3]=Math.max(result[3],y);
  }else for(const child of value)stack.push(child);}return result;
}
export function viewportStatusText(status:string,shown=0,matched:number|null=null){
  if(status==='DISABLED')return 'เปิดเลเยอร์น้ำท่วมเพื่อโหลดขอบเขตในกรอบจอ';
  if(status==='AVAILABLE')return `โหลดขอบเขตที่อาจตัดกรอบแผนที่ครบ ${shown.toLocaleString()} รูปพื้นที่`;
  if(status==='PARTIAL')return `แสดง ${shown.toLocaleString()} จาก ${matched?.toLocaleString()??'ไม่ทราบจำนวน'} รูปพื้นที่ที่อาจตัดกรอบจอ · ยังไม่ครบ กรุณาซูมเข้า หรือเลือกดูรายการพื้นที่`;
  if(status==='EMPTY')return 'ไม่พบรูปพื้นที่จากชุดย้อนหลังนี้ที่ตัดกรอบจอ · ไม่ยืนยันว่าไม่มีน้ำท่วม';
  if(status==='ZOOM_REQUIRED')return 'ซูมเข้าเพื่อโหลดขอบเขตเฉพาะบริเวณที่มองเห็น · มุมมองกว้างแสดงจำนวนสรุป';
  if(status==='INDEX_UNAVAILABLE')return 'ดัชนีตำแหน่งของชุดนี้ยังไม่พร้อม · เลือกรายการของพื้นที่เพื่อดูขอบเขตได้';
  if(status==='GEOMETRY_UNAVAILABLE')return 'ชุดนี้เหลือข้อมูลสรุป ขอบเขตหมดช่วงเก็บรักษา';
  if(status==='MOVING')return 'กำลังเลื่อนหรือซูมแผนที่ · หยุดเพื่อโหลดขอบเขตบริเวณใหม่';
  if(status==='FAILED')return 'โหลดขอบเขตในกรอบจอไม่สำเร็จ · ยังไม่ทราบข้อมูลของมุมมองนี้';
  return 'กำลังโหลดขอบเขตในกรอบแผนที่';
}
