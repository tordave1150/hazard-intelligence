import type {Metadata} from 'next';
import TimeThemeProvider from '@/components/time-theme';
import './globals.css';
import 'maplibre-gl/dist/maplibre-gl.css';
export const metadata:Metadata={title:'Thailand Hazard Intelligence | Weather & Water',description:'One map for Thailand weather and water situation awareness, with source attribution and data age.'};
export default function Layout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body><TimeThemeProvider>{children}</TimeThemeProvider></body></html>;
}
