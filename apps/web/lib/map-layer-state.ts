import type {DashboardMode} from './dashboard-mode';

export type MapBackground='off'|'daily'|'hourly';
type Geography='administrative'|'basin';
export function effectiveBackground(mode:DashboardMode,enabled:boolean,geography:Geography):MapBackground{
  return !enabled||geography==='basin'||mode==='situation'?'off':mode;
}
export function backgroundAvailable(background:MapBackground,date:string,today:string,geography:Geography){
  return background==='off'||(geography==='administrative'&&(background==='daily'||date===today));
}
