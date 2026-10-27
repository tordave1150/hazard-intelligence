import {areaById} from './geography';
import {invalid,json} from './http';
export function unavailable(request:Request,source:string) {
  const q=new URL(request.url).searchParams,id=q.get('area_id');
  if(id&&!areaById.has(id))return invalid('Unknown area',404);
  if(q.has('kind')&&!['rain','river'].includes(q.get('kind')!))return invalid('Invalid gauge kind');
  const reason=source==='gistda'
    ?'API access verified; one 30-day sample passed syntax/topology checks. Acquisition, provider CRS/coverage and resource-specific display permission remain unaccepted'
    :'Source access, permission and sample acceptance are pending';
  return json({records:[],status:'UNAVAILABLE',source_id:source,integration_status:'planned',reason});
}
