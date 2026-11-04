import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
export const dynamic='force-dynamic';
export async function GET(_request:Request,{params}:{params:Promise<{id:string}>}){
  if(process.env.NODE_ENV==='production'||process.env.HAZARD_LOCAL_SNAPSHOT!=='1')return new Response(null,{status:404});
  const {id}=await params;if(!/^[a-f0-9]{64}$/.test(id))return new Response(null,{status:404});
  try{
    const payload=JSON.parse(await readFile(path.join(process.cwd(),'data/local/radar-capture.json'),'utf8'));
    const frame=payload.frames.find((f:{sha256:string})=>f.sha256===id);if(!frame)return new Response(null,{status:404});
    const bytes=Buffer.from(frame.image_base64,'base64');if(createHash('sha256').update(bytes).digest('hex')!==id)return new Response(null,{status:404});
    return new Response(bytes,{headers:{'Content-Type':'image/png','Cache-Control':'public, max-age=3600'}});
  }catch{return new Response(null,{status:404});}
}
