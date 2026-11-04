import base64
import hashlib
import re
import struct
import time
import zlib
from datetime import datetime, timezone
import requests

BASE='https://weather.tmd.go.th/composite/'
COORDINATES=[[95,22.5],[108,22.5],[108,4],[95,4]]
MAX_FRAME_BYTES=800_000
MAX_TOTAL_BYTES=2_800_000


def parse_list(text, now):
    if len(text.encode())>16384:raise ValueError('Oversized frame list')
    rows=[]
    for line in text.splitlines():
        if not line.strip():continue
        match=re.fullmatch(r'background_THA\.png "(\d{4}-\d{2}-\d{2} \d{2}:\d{2})" overlay=(zr/\d{2}\.png)',line.strip())
        if not match:raise ValueError('Unsupported frame list')
        stamp=datetime.strptime(match[1],'%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
        if stamp.minute%15 or stamp.timestamp()>now+300:raise ValueError('Invalid frame time')
        rows.append({'observed_at':stamp.isoformat(timespec='seconds').replace('+00:00','Z'),'path':match[2]})
    if not 1<=len(rows)<=25:raise ValueError('Invalid frame count')
    times=[r['observed_at'] for r in rows]
    if times!=sorted(set(times)) or len(set(r['path'] for r in rows))!=len(rows):raise ValueError('Duplicate or unordered frames')
    latest=datetime.fromisoformat(times[-1].replace('Z','+00:00')).timestamp()
    if now-latest>5400:raise ValueError('Source radar images stale')
    return [r for r in rows if latest-datetime.fromisoformat(r['observed_at'].replace('Z','+00:00')).timestamp()<=10800][-13:]


def validate_png(data):
    if not 57<=len(data)<=MAX_FRAME_BYTES or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
    pos=8;compressed=bytearray();width=height=0;ended=False;header=False
    while pos+12<=len(data):
        size=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];end=pos+12+size
        if end>len(data):raise ValueError('Truncated PNG')
        payload=data[pos+8:pos+8+size]
        if zlib.crc32(kind+payload)&0xffffffff!=struct.unpack_from('>I',data,pos+8+size)[0]:raise ValueError('PNG checksum mismatch')
        if not header and kind!=b'IHDR':raise ValueError('PNG header missing')
        if kind==b'IHDR':
            if header or size!=13:raise ValueError('Invalid PNG header')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',payload)
            if (width,height,depth,color,compression,filtering,interlace)!=(1800,2644,8,6,0,0,0):raise ValueError('Unsupported radar dimensions or format')
            header=True
        elif kind==b'IDAT':compressed.extend(payload)
        elif kind==b'IEND':
            if size or end!=len(data):raise ValueError('PNG trailing bytes')
            ended=True;break
        elif kind[0]&32==0:raise ValueError('Unsupported PNG chunk')
        pos=end
    if not ended or not compressed:raise ValueError('Incomplete PNG')
    expected=height*(1+width*4);decoder=zlib.decompressobj()
    raw=decoder.decompress(compressed,expected+1)
    if len(raw)!=expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:raise ValueError('Invalid PNG image stream')
    if any(raw[i]>4 for i in range(0,len(raw),1+width*4)):raise ValueError('Invalid PNG row filter')
    return {'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest(),'byte_length':len(data)}


def capture(get=None,now=None):
    started=time.monotonic();get=get or requests.get;now=now or time.time()
    def fetch(url,limit):
        if time.monotonic()-started>180:raise ValueError('Capture time budget exceeded')
        with get(url,timeout=(10,20),stream=True,allow_redirects=False,headers={'User-Agent':'HazardIntelligence/1.0 (noncommercial radar display)'}) as response:
            if response.status_code!=200:raise ValueError('Radar source request failed')
            data=bytearray()
            for chunk in response.iter_content(8192):
                if time.monotonic()-started>180:raise ValueError('Capture time budget exceeded')
                data.extend(chunk)
                if len(data)>limit:raise ValueError('Radar byte budget exceeded')
            return bytes(data)
    viewer=fetch(BASE+'index_composite.html',200000).decode('utf-8')
    section=re.search(r'RADAR_COORDS\s*:\s*\[(.*?)\]\s*,\s*BASEMAP',viewer,re.S)
    coordinates=[[float(a),float(b)] for a,b in re.findall(r'\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]',section[1] if section else '')]
    utc=re.search(r"new Date\(date\s*\+\s*['\"]T['\"]\s*\+\s*time\s*\+\s*['\"]:00Z['\"]\)",viewer)
    if coordinates!=COORDINATES or 'PCAPPI Z-R' not in viewer or 'mm/hr' not in viewer or not utc:
        raise ValueError('Source viewer geometry, units or time convention changed')
    listing=fetch(BASE+'images_composite.list',16384);clock=fetch(BASE+'radar.sharing.latest',128)
    rows=parse_list(listing.decode('utf-8'),now)
    latest=rows[-1]['observed_at'].replace('T',' ')[:16]
    if clock.decode('utf-8').strip()!=latest:raise ValueError('Source clocks disagree')
    frames=[];total=0
    for row in rows:
        data=fetch(BASE+'images/'+row['path'],MAX_FRAME_BYTES);total+=len(data)
        if total>MAX_TOTAL_BYTES:raise ValueError('Generation byte budget exceeded')
        frame={**row,**validate_png(data),'image_base64':base64.b64encode(data).decode('ascii')};frames.append(frame)
    for row in frames:
        data=fetch(BASE+'images/'+row['path'],MAX_FRAME_BYTES)
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Mutable image changed during capture')
    if listing!=fetch(BASE+'images_composite.list',16384) or clock!=fetch(BASE+'radar.sharing.latest',128):raise ValueError('Generation changed during capture')
    return {'schema_version':'2.0','source_id':'tmd_radar','product_id':'composite_rain_rate','data_state':'radar_estimate',
        'snapshot_id':'latest','fetched_at':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'source_url':BASE+'index_composite.html','coordinates':COORDINATES,'units':'mm/hour',
        'generation_consistency':'MANIFEST_CLOCK_AND_DOUBLE_IMAGE_HASH_CHECKED_NO_VERSION_TOKEN',
        'frames':frames}
