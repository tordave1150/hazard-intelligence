"""Preserve CAP times, agency classifications, references and original polygons."""
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import timezone
from pipelines.shared.time_units import instant,utc_now
from pipelines.shared.schemas import validate_record
from .data import SOURCE,PRODUCT,MAX_ITEMS,allowed_document,mapped_provinces,warning_time_quality

NS={'c':'urn:oasis:names:tc:emergency:cap:1.2'}


def xml(raw):
    if len(raw)>2*1024*1024 or b'\x00' in raw or b'<!doctype' in raw.lower() or b'<!entity' in raw.lower():
        raise ValueError('Unsupported or oversized XML')
    raw.decode('utf-8') # This accepted product uses UTF-8; reject alternate-encoding entity bypasses.
    return ET.fromstring(raw)


def utc(value):return instant(value).isoformat().replace('+00:00','Z')


def feed_index(raw):
    root=xml(raw)
    if root.tag!='rss' or root.attrib.get('version')!='2.0':raise ValueError('Not a CAP RSS feed')
    channel=root.find('channel')
    if channel is None or channel.findtext('copyright')!='public domain':raise ValueError('CAP feed terms changed')
    generated=parsedate_to_datetime(channel.findtext('lastBuildDate'))
    if generated.tzinfo is None:raise ValueError('Missing feed timezone')
    items=[{'id':item.findtext('guid'),'url':item.findtext('link')} for item in channel.findall('item')]
    if len(items)>MAX_ITEMS or len({i['id'] for i in items})!=len(items):raise ValueError('Invalid CAP feed size or duplicate identity')
    for item in items:
        if not item['url'] or not allowed_document(item['url']) or item['url'].rsplit('/CAP',1)[-1][:-4]!=item['id']:
            raise ValueError('CAP feed contains unverified document link')
    return items,generated.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def normalize(raw,content_ref,fetched_at):
    root=xml(raw)
    if root.tag!='{'+NS['c']+'}alert':raise ValueError('Not CAP 1.2')
    text=lambda node,name:node.findtext('c:'+name,namespaces=NS)
    if text(root,'status')!='Actual' or text(root,'scope')!='Public':return None
    kind=text(root,'msgType')
    if kind not in ['Alert','Update','Cancel']:raise ValueError('Unsupported public CAP message type')
    infos=root.findall('c:info',NS)
    thai=[i for i in infos if (text(i,'language') or '').lower().startswith('th')]
    if len(thai)==1:info=thai[0]
    elif len(infos)==1:info=infos[0]
    elif not infos and kind=='Cancel':info=None
    else:raise ValueError('CAP language/information selection requires review')
    get=lambda key:text(info,key) if info is not None else None
    issued=utc(text(root,'sent'))
    refs=[]
    for ref in (text(root,'references') or '').split():
        sender,identity,sent=ref.split(',');refs.append({'sender':sender,'warning_id':identity,'issued_at':utc(sent)})
    areas=[];polygons=[]
    for area in info.findall('c:area',NS) if info is not None else []:
        if area.find('c:circle',NS) is not None:raise ValueError('CAP circles require separate product acceptance')
        geocodes=[{'value_name':text(g,'valueName'),'value':text(g,'value')} for g in area.findall('c:geocode',NS)]
        areas.append({'description':text(area,'areaDesc'),'geocodes':geocodes})
        for polygon in area.findall('c:polygon',NS):
            # CAP lists latitude,longitude; GeoJSON requires longitude,latitude.
            polygons.append([[[float(pair.split(',')[1]),float(pair.split(',')[0])] for pair in polygon.text.split()]])
    row={'schema_version':'2.0','source_id':'tmd','product_id':PRODUCT,'data_state':'agency_warning',
        'warning_id':text(root,'identifier'),'sender':text(root,'sender'),'message_type':kind,'status':'Actual','scope':'Public',
        'references':refs,'issued_at':issued,'fetched_at':fetched_at,'ingested_at':utc_now(),
        'effective_start':utc(get('effective')) if get('effective') else issued if info is not None else None,
        'effective_time_source':'CAP effective' if get('effective') else 'CAP sent' if info is not None else 'not supplied',
        'expires_at':utc(get('expires')) if get('expires') else None,
        'language':get('language'),'event':get('event'),'headline':get('headline') or get('event'),
        'description':get('description'),'instruction':get('instruction'),'agency_severity':get('severity'),
        'urgency':get('urgency'),'certainty':get('certainty'),'area_ids':sorted(mapped_provinces(areas)),'source_areas':areas,
        'geometry':{'type':'MultiPolygon','coordinates':polygons} if polygons else None,
        'content_ref':content_ref,'source_url':SOURCE,'terms_url':'https://www.tmd.go.th/content/copyright'}
    row['time_quality']=warning_time_quality(row)
    return validate_record('AgencyWarning',row)


def make_feed(items,generated,records,fetched_at,ignored=0):
    return validate_record('WarningFeed',{'schema_version':'2.0','source_id':'tmd','product_id':PRODUCT,
        'data_state':'agency_warning','snapshot_id':'latest','fetched_at':fetched_at,'ingested_at':utc_now(),
        'feed_generated_at':generated,'feed_url':SOURCE,'feed_copyright':'public domain',
        'feed_item_count':len(items),'ignored_item_count':ignored,'records':records})
