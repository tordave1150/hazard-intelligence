"""Bounded public QPE/rain-rate metadata inspection; never ingests a numerical grid."""
import argparse,hashlib,json,struct
from datetime import datetime,timezone
from pathlib import Path
import requests

ROOT='https://weather.tmd.go.th/composite/data/'


def prefix(url):
    with requests.get(url,stream=True,allow_redirects=False,timeout=(10,25),headers={'Range':'bytes=0-65535','User-Agent':'HazardIntelligence/1.0 (bounded metadata review)'}) as response:
        if response.status_code not in (200,206):raise ValueError('Public source unavailable')
        data=bytearray()
        for part in response.iter_content(8192):
            data.extend(part[:65536-len(data)])
            if len(data)==65536:break
        return bytes(data)


def netcdf_header(data):
    if data[:4]!=b'CDF\x01':raise ValueError('Unsupported NetCDF format')
    offset=8
    def integer():
        nonlocal offset
        value=struct.unpack_from('>I',data,offset)[0];offset+=4;return value
    def string():
        nonlocal offset
        count=integer()
        if count>4096:raise ValueError('Metadata string limit')
        value=data[offset:offset+count].decode('utf-8');offset+=(count+3)//4*4;return value
    def attributes():
        nonlocal offset
        tag,count=integer(),integer()
        if tag==0 and count==0:return {}
        if tag!=12 or count>100:raise ValueError('Invalid attribute list')
        result={};formats={1:('b',1),3:('h',2),4:('i',4),5:('f',4),6:('d',8)}
        for _ in range(count):
            name=string();kind,n=integer(),integer()
            if n>4096:raise ValueError('Attribute value limit')
            if kind==2:value=data[offset:offset+n].decode('utf-8');size=n
            elif kind in formats:
                fmt,size=formats[kind];size*=n;value=list(struct.unpack_from('>'+fmt*n,data,offset))
            else:raise ValueError('Unsupported metadata type')
            offset+=(size+3)//4*4;result[name]=value
        return result
    tag,count=integer(),integer()
    if tag!=10 or count>8:raise ValueError('Invalid dimensions')
    dims=[{'name':string(),'length':integer()} for _ in range(count)]
    attrs=attributes();tag,count=integer(),integer()
    if tag!=11 or count>16:raise ValueError('Invalid variable list')
    variables=[]
    for _ in range(count):
        name=string();ndims=integer()
        if ndims>8:raise ValueError('Variable dimension limit')
        ids=[integer() for _ in range(ndims)];properties=attributes();kind,size,begin=integer(),integer(),integer()
        variables.append({'name':name,'dimension_ids':ids,'attributes':properties,'netcdf_type':kind,'declared_bytes':size,'begin':begin})
    axes={}
    for v in variables:
        if v['name'] not in ('latitude','longitude') or len(v['dimension_ids'])!=1 or v['netcdf_type'] not in (5,6):continue
        n=dims[v['dimension_ids'][0]]['length'];width=8 if v['netcdf_type']==6 else 4
        if not 1<=n<=20000 or v['begin']+n*width>len(data):continue
        values=struct.unpack_from('>'+('d' if width==8 else 'f')*n,data,v['begin'])
        axes[v['name']]={'count':n,'first':values[0],'last':values[-1],'increasing':all(a<b for a,b in zip(values,values[1:]))}
    return {'dimensions':dims,'global_attributes':attrs,'variables':variables,'header_parsed_bytes':offset,'coordinate_axes':axes}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--export',type=Path);args=parser.parse_args()
    report={'reviewed_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'state':'NOT_ACCEPTED','publishes_grid':False,'sources':{}}
    for name in ['composite.nc','composite.ascii']:
        try:
            data=prefix(ROOT+name);entry={'url':ROOT+name,'prefix_bytes':len(data),'prefix_sha256':hashlib.sha256(data).hexdigest()}
            if name.endswith('.nc'):
                entry.update(netcdf_header(data));variable=next((v for v in entry['variables'] if len(v['dimension_ids'])>=2),{})
                a=variable.get('attributes',{});entry['quantity_description_supplied']=a.get('long_name') not in (None,'','desc')
                entry['nonplaceholder_units_supplied']=a.get('units') not in (None,'','unit','unknown')
            else:
                entry['grid_header']={line.split()[0].lower():line.split()[1] for line in data.decode('ascii').splitlines()[:6] if len(line.split())==2}
            report['sources'][name]=entry
        except (requests.RequestException,ValueError,UnicodeError,struct.error,IndexError) as exc:report['sources'][name]={'url':ROOT+name,'error_type':type(exc).__name__}
    nc=report['sources'].get('composite.nc',{});ascii_grid=report['sources'].get('composite.ascii',{}).get('grid_header',{})
    axes=nc.get('coordinate_axes',{})
    if 'latitude' in axes and 'longitude' in axes and all(k in ascii_grid for k in ['xllcorner','yllcorner','cellsize']):
        cell=float(ascii_grid['cellsize'])
        report['grid_registration_comparison']={'interpretation':'Conventional ASCII corner-to-cell-center comparison; not a provider alignment declaration',
            'netcdf_south':axes['latitude']['first'],'netcdf_west':axes['longitude']['first'],
            'ascii_south_cell_center':float(ascii_grid['yllcorner'])+cell/2,'ascii_west_cell_center':float(ascii_grid['xllcorner'])+cell/2,
            'state':'NEEDS_PROVIDER_CONFIRMATION'}
    report['unresolved_gates']=['SCIENTIFIC_QUANTITY_AND_UNITS','INSTANTANEOUS_OR_ACCUMULATION_DEFINITION','ASCII_NETCDF_GRID_REGISTRATION','NUMERICAL_REUSE_AND_VALID_NO_DATA_CONTRACT']
    output=json.dumps(report,ensure_ascii=True,indent=2)+'\n'
    if args.export:args.export.parent.mkdir(parents=True,exist_ok=True);args.export.write_text(output,encoding='utf-8')
    print(output)


if __name__=='__main__':main()
