import {createHash} from 'node:crypto';
import {inflateSync} from 'node:zlib';
// CRC protects against a truncated/corrupt image before its immutable hash is trusted.
function crc(bytes:Buffer){let value=0xffffffff;for(const b of bytes){value^=b;for(let i=0;i<8;i++)value=(value>>>1)^((value&1)?0xedb88320:0);}return (value^0xffffffff)>>>0;}
export function radarPng(data:Buffer){
  if(data.length<57||data.length>800000||!data.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))throw Error('Invalid PNG');
  let pos=8,header=false,ended=false;const parts:Buffer[]=[];
  while(pos+12<=data.length){
    const size=data.readUInt32BE(pos),end=pos+12+size;
    if(end>data.length)throw Error('Truncated PNG');
    const kind=data.toString('ascii',pos+4,pos+8),body=data.subarray(pos+8,pos+8+size);
    if(crc(data.subarray(pos+4,pos+8+size))!==data.readUInt32BE(pos+8+size))throw Error('PNG checksum mismatch');
    if(!header&&kind!=='IHDR')throw Error('Missing PNG header');
    if(kind==='IHDR'){
      if(header||size!==13||body.readUInt32BE(0)!==1800||body.readUInt32BE(4)!==2644||!body.subarray(8).equals(Buffer.from([8,6,0,0,0])))throw Error('Unsupported PNG');
      header=true;
    }else if(kind==='IDAT')parts.push(body);
    else if(kind==='IEND'){if(size||end!==data.length)throw Error('PNG trailing data');ended=true;break;}
    else if((data[pos+4]&32)===0)throw Error('Unsupported critical PNG chunk');
    pos=end;
  }
  const expected=2644*(1+1800*4);
  if(!ended||!parts.length)throw Error('Incomplete PNG');
  const result=inflateSync(Buffer.concat(parts),{maxOutputLength:expected+1,info:true}) as unknown as {buffer:Buffer;engine:{bytesWritten:number}};
  if(result.buffer.length!==expected||result.engine.bytesWritten!==Buffer.concat(parts).length)throw Error('Invalid PNG stream');
  for(let i=0;i<expected;i+=7201)if(result.buffer[i]>4)throw Error('Invalid PNG filter');
  return {sha256:createHash('sha256').update(data).digest('hex'),byte_length:data.length,width:1800 as const,height:2644 as const};
}
