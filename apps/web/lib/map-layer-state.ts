import type {DashboardMode} from './dashboard-mode';

export type MapBackground='off'|'daily'|'hourly'|'radar';
type Geography='administrative'|'basin';
export function effectiveBackground(mode:DashboardMode,enabled:boolean,geography:Geography,radar=false):MapBackground{
  if(radar)return 'radar';
  return !enabled||geography==='basin'||mode==='situation'?'off':mode;
}
export function backgroundAvailable(background:MapBackground,date:string,today:string,geography:Geography){
  return background==='radar'||background==='off'||(geography==='administrative'&&(background==='daily'||date===today));
}
