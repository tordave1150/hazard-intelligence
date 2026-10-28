'use client';
import {createContext,useContext,useEffect,useState} from 'react';
import {timeTheme,type TimeTheme} from '@/lib/map-theme';
const TimeContext=createContext<{now:number|null;theme:TimeTheme}>({now:null,theme:'day'});
export const useTimeTheme=()=>useContext(TimeContext);
export default function TimeThemeProvider({children,clock=Date.now}:{children:React.ReactNode;clock?:()=>number}){
  const [now,setNow]=useState<number|null>(null);
  const theme=now===null?'day':timeTheme(now);
  const ready=now!==null;
  useEffect(()=>{
    const update=()=>setNow(clock());update();
    const timer=setInterval(update,60000);
    const resume=()=>{if(document.visibilityState==='visible')update();};
    document.addEventListener('visibilitychange',resume);window.addEventListener('focus',update);
    return()=>{clearInterval(timer);document.removeEventListener('visibilitychange',resume);window.removeEventListener('focus',update);};
  },[clock]);
  useEffect(()=>{if(ready)document.documentElement.dataset.timeTheme=theme;},[theme,ready]);
  return <TimeContext.Provider value={{now,theme}}>{children}</TimeContext.Provider>;
}
