import {areas,areaById} from '@/lib/geography';
import {contains} from '@/lib/semantics';
import {invalid,json} from '@/lib/http';
export async function GET(request: Request) {
  const q=new URL(request.url).searchParams;
  const level=q.get('level'), parent=q.get('parent_id'), search=q.get('q')?.trim().toLowerCase()??'';
  if(level&&!['national','region','province','district','basin'].includes(level))return invalid('Invalid geographic level');
  if(parent&&!areaById.has(parent))return invalid('Unknown parent area',404);
  if(search.length>100)return invalid('Search is too long');
  const root=parent?areaById.get(parent):null;
  return json({areas:areas.filter(a=>(!level||a.level===level)&&(!root||contains(root,a))&&
    (!search||`${a.name} ${a.name_th} ${a.id}`.toLowerCase().includes(search))).slice(0,1200)});
}
