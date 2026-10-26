import {NextResponse} from 'next/server';
export function json(data: unknown, status=200) {
  return NextResponse.json(data,{status,headers:{'Cache-Control':status===200?'public, s-maxage=60, stale-while-revalidate=120':'no-store'}});
}
export function invalid(message: string, status=400) {return json({error:message},status);}
