import type {Freshness,Source} from './types';

const policies:Record<string,{hours:number;grace:number;workflow:string;utcHours:number[];minute:number;pollMinutes?:number[];dueHours?:number}>={
  open_meteo:{hours:24,grace:6,workflow:'etl.yml',utcHours:[1],minute:0},rid:{hours:24,grace:6,workflow:'rid.yml',utcHours:[1],minute:15},
  tmd:{hours:1,grace:1,workflow:'tmd.yml',utcHours:Array.from({length:24},(_,i)=>i),minute:11,pollMinutes:[11,41],dueHours:1},
  gistda:{hours:24,grace:6,workflow:'gistda.yml',utcHours:[2],minute:27},
  open_meteo_hourly:{hours:4,grace:2,workflow:'hourly.yml',utcHours:Array.from({length:24},(_,i)=>i),minute:23,dueHours:4},
  thaiwater_rain:{hours:2,grace:1,workflow:'thaiwater.yml',utcHours:Array.from({length:12},(_,i)=>i*2),minute:43},
  thaiwater:{hours:2,grace:1,workflow:'thaiwater.yml',utcHours:Array.from({length:12},(_,i)=>i*2),minute:43},
};
const repository='https://github.com/tordave1150/hazard-intelligence';
export type RuntimeSource=Source & {freshness:Freshness;query_freshness?:Freshness;available?:boolean;
  health:Record<string,unknown>|null;storage:string|null;monitoring:SourceMonitoring};
export type SourceMonitoring={state:'OK'|'ATTENTION'|'FAILED'|'OVERDUE'|'RUNNING'|'STALLED'|'UNKNOWN'|'PLANNED';
  needs_attention:boolean;cadence_hours:number|null;overdue:boolean;quality_issue_count:number;
  attempt_age_hours:number|null;success_age_hours:number|null;expected_by:string|null;actions_url:string|null;run_url:string|null;reason:string};
function age(value:unknown,now:number){
  const time=typeof value==='string'?Date.parse(value):NaN;
  return Number.isFinite(time)&&time<=now+300000?Math.max(0,(now-time)/3600000):null;
}
export function monitorSource(id:string,freshness:Freshness,health:Record<string,unknown>|null,now=Date.now()):SourceMonitoring{
  const policy=policies[id],attempt=age(health?.last_attempt,now),success=age(health?.last_success,now);
  let expected:number|null=null;
  if(policy&&attempt!==null){
    const last=now-attempt*3600000,date=new Date(last);
    const midnight=Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),date.getUTCDate());
    let due=policy.dueHours&&success!==null?now-success*3600000+policy.dueHours*3600000:last;
    if(id==='open_meteo_hourly'&&success!==null){
      const bangkok=new Date(now-success*3600000+7*3600000);
      const nextDay=Date.UTC(bangkok.getUTCFullYear(),bangkok.getUTCMonth(),bangkok.getUTCDate()+1)-7*3600000;
      due=Math.min(due,nextDay);
    }
    const slots=[0,1,2].flatMap(day=>policy.utcHours.flatMap(hour=>(policy.pollMinutes??[policy.minute]).map(minute=>midnight+day*86400000+hour*3600000+minute*60000)));
    expected=slots.filter(slot=>slot>last&&slot>=due).sort((a,b)=>a-b)[0]+policy.grace*3600000;
  }
  const overdue=expected!==null&&now>expected;
  const quality=Number.isInteger(health?.quality_issue_count)&&Number(health?.quality_issue_count)>0?Number(health?.quality_issue_count):0;
  const run=typeof health?.run_url==='string'&&/^https:\/\/github\.com\/tordave1150\/hazard-intelligence\/actions\/runs\/[0-9]+$/.test(health.run_url)?health.run_url:null;
  let state:SourceMonitoring['state']=!policy?'PLANNED':health?.status==='FAILED'?'FAILED':
    health?.status==='RUNNING'?(attempt!==null&&attempt>1/3?'STALLED':'RUNNING'):
    overdue?'OVERDUE':quality||['DELAYED','STALE','UNAVAILABLE'].includes(freshness)?'ATTENTION':
    !health||attempt===null||success===null||freshness==='UNKNOWN'?'UNKNOWN':'OK';
  const reason=state==='PLANNED'?'ยังไม่มีแหล่งข้อมูลปัจจุบันที่ผ่านการตรวจรับ':state==='FAILED'?'รอบล่าสุดล้มเหลว กำลังเก็บชุดข้อมูลที่สำเร็จล่าสุดไว้':
    state==='STALLED'?'เริ่มรันแล้วแต่ยังไม่มีผลจบเกิน 20 นาที ตรวจประวัติรัน':state==='RUNNING'?'กำลังดึงและตรวจข้อมูล ชุดก่อนหน้ายังใช้งานอยู่':
    state==='OVERDUE'?'ยังไม่พบรอบใหม่ภายในช่วงเป้าหมายและเวลาผ่อนผัน':quality?`ข้อมูลต้นทางมีปัญหาคุณภาพ ${quality} รายการ รายการอื่นยังใช้งานได้`:
    state==='ATTENTION'?'มีข้อมูลล่าช้า เก่า หรือยังไม่มีชุดที่อ่านได้':state==='UNKNOWN'?'หลักฐานเวลาอัปเดตยังไม่ครบ':
    id==='gistda'?'การดึงข้อมูลเป็นปัจจุบัน แต่ไม่ทราบเวลาถ่ายภาพดาวเทียม':id.startsWith('thaiwater')?'การดึงข้อมูลเป็นปัจจุบัน เวลาตรวจวัดยังไม่ระบุเขตเวลา':'รอบล่าสุดสำเร็จและอยู่ในช่วงความสดที่กำหนด';
  return {state,needs_attention:['ATTENTION','FAILED','OVERDUE','STALLED','UNKNOWN'].includes(state),cadence_hours:policy?.hours??null,
    overdue,quality_issue_count:quality,attempt_age_hours:attempt,success_age_hours:success,
    expected_by:expected!==null?new Date(expected).toISOString():null,
    actions_url:policy?`${repository}/actions/workflows/${policy.workflow}`:null,run_url:run,reason};
}
export function healthError(health:Record<string,unknown>|null){
  if(health?.status!=='FAILED')return null;
  const reasons:Record<string,string>={rate_limited:'ต้นทางจำกัดอัตราการเรียกข้อมูล',request_budget_exhausted:'ใช้โควตาร่วมที่กำหนดไว้ครบแล้ว',
    upstream_unavailable:'บริการต้นทางไม่พร้อมใช้งาน',transport_error:'เชื่อมต่อต้นทางไม่สำเร็จ',http_error:'ต้นทางตอบปฏิเสธคำขอ',
    http_permanent:'ต้นทางตอบปฏิเสธคำขอ',invalid_json:'รูปแบบคำตอบจากต้นทางไม่ถูกต้อง',
    ValueError:'ข้อมูลไม่ผ่านการตรวจรูปแบบหรือความครบถ้วน',ValidationError:'ข้อมูลไม่ผ่านสัญญาข้อมูล',
    collection_deadline:'ดึงข้อมูลไม่เสร็จภายในเวลาที่กำหนด'};
  return reasons[String(health.error_summary)]??'ดูรายละเอียดของรอบที่ล้มเหลวใน GitHub Actions';
}
