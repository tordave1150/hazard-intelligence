import {bangkokDate} from './semantics';
export type DashboardMode='situation'|'daily'|'hourly';
export function dashboardDates(now:number){
  const today=bangkokDate(now),start=Date.parse(today+'T12:00:00+07:00');
  return Array.from({length:4},(_,i)=>bangkokDate(start+i*86400000));
}
export const dashboardMode=(date:string,today:string,preference:DashboardMode):DashboardMode=>date===today?preference:'daily';
