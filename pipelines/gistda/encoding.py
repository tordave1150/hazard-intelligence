"""Lossless bounded storage encodings. Coordinates remain IEEE-754 doubles."""
import gzip
import hashlib
import json
import zlib
import msgpack

VERSIONS=('gzip-v1','msgpack-gzip-v1')
CURRENT_VERSION=VERSIONS[-1]
RAW_LIMIT=1024*1024


def binary_rows(rows):
    # Never enable use_single_float: that would round the source coordinates.
    return msgpack.packb(rows,use_bin_type=True,use_single_float=False,strict_types=True)


def unpacked(raw,version):
    if version=='gzip-v1':return json.loads(raw)
    if version!=CURRENT_VERSION:raise ValueError('Unsupported flood storage encoding')
    return msgpack.unpackb(raw,raw=False,strict_map_key=True,max_str_len=256,
                          max_bin_len=0,max_ext_len=0,max_array_len=131072,max_map_len=8)


def checked_raw(descriptor,data):
    if len(data)!=descriptor['compressed_bytes'] or not 0<descriptor['raw_bytes']<=RAW_LIMIT:raise ValueError('Invalid compressed chunk size')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS);raw=decoder.decompress(data,RAW_LIMIT+1)
    if len(raw)!=descriptor['raw_bytes'] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or hashlib.sha256(raw).hexdigest()!=descriptor['hash']:raise ValueError('Invalid compressed chunk identity')
    return raw


def pack_rows(rows):
    raw=binary_rows(rows)
    if len(raw)>RAW_LIMIT:raise ValueError('Flood chunk byte limit exceeded')
    return raw,gzip.compress(raw,mtime=0)
