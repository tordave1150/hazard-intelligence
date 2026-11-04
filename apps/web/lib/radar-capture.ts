import {validatedRadar,type RadarManifest} from './radar';
import {radarPng} from './radar-png';
type Candidate=Omit<RadarManifest,'frames'>&{frames:{observed_at:string;path:string;image_base64:string;sha256:string;byte_length:number;width:number;height:number}[]};
export function decodedRadarCandidate(value:unknown,now=Date.now()){
  if(!value||typeof value!=='object')throw Error('Invalid radar capture');
  const candidate=value as Candidate;
  if(!Array.isArray(candidate.frames)||!candidate.frames.length||candidate.frames.length>13)throw Error('Invalid frame count');
  const images=new Map<string,Buffer>();let total=0;
  const frames=candidate.frames.map(frame=>{
    if(!/^zr\/\d{2}\.png$/.test(frame.path)||typeof frame.image_base64!=='string'||frame.image_base64.length>1066668||
      !/^[A-Za-z0-9+/]*={0,2}$/.test(frame.image_base64)||Object.keys(frame).some(k=>!['observed_at','path','image_base64','sha256','byte_length','width','height'].includes(k)))throw Error('Invalid image capture');
    const bytes=Buffer.from(frame.image_base64,'base64');
    total+=bytes.length;if(total>2800000)throw Error('Image byte budget exceeded');
    if(bytes.toString('base64')!==frame.image_base64)throw Error('Invalid image encoding');
    const checked=radarPng(bytes);
    if(checked.sha256!==frame.sha256||checked.byte_length!==frame.byte_length||frame.width!==1800||frame.height!==2644)throw Error('Image identity mismatch');
    images.set(frame.sha256,bytes);
    return {observed_at:frame.observed_at,...checked,url:'https://capture.public.blob.vercel-storage.com/tmd-radar/'+frame.observed_at.replace(/[-:]/g,'')+'-'+checked.sha256+'.png'};
  });
  const original=validatedRadar({...candidate,frames});
  // Enforce the upload policy even for queued producers using the legacy cadence.
  const selected=original.frames.filter(frame=>Date.parse(frame.observed_at)%1800000===0);
  const feed=validatedRadar({...original,sampling_minutes:30,frames:selected});
  if(Date.parse(feed.fetched_at)>now+300000||now-Date.parse(feed.fetched_at)>600000||now-Date.parse(feed.frames.at(-1)!.observed_at)>5400000)throw Error('Stale capture');
  return {feed,images};
}
