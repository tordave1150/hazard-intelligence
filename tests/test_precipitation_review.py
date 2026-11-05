import struct,json
import pytest
from scripts import inspect_precipitation as review


def header():
    integer=lambda n:struct.pack('>I',n)
    def string(s):
        b=s.encode();return integer(len(b))+b+b'\0'*((-len(b))%4)
    dims=integer(10)+integer(2)+string('latitude')+integer(1)+string('longitude')+integer(1)
    attrs=integer(12)+integer(2)+string('units')+integer(2)+string('mm')+string('long_name')+integer(2)+string('precipitation')
    return b'CDF\x01'+integer(0)+dims+integer(0)*2+integer(11)+integer(1)+string('rain')+integer(2)+integer(0)+integer(1)+attrs+integer(5)+integer(4)+integer(0)


def test_metadata_parser_reads_supplied_units_without_accepting_a_scientific_product():
    value=review.netcdf_header(header())
    assert value['variables'][0]['attributes']['units']=='mm'
    assert value['dimensions'][0]['name']=='latitude'
    with pytest.raises(ValueError):review.netcdf_header(b'not netcdf')


def test_range_ignored_response_stops_at_prefix_limit(monkeypatch):
    yielded=[]
    class Response:
        status_code=200
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def iter_content(self,n):
            for i in range(100):yielded.append(i);yield b'x'*8192
    monkeypatch.setattr(review.requests,'get',lambda *a,**k:Response())
    assert len(review.prefix(review.ROOT+'composite.nc'))==65536 and len(yielded)==8


def test_even_nonplaceholder_units_do_not_silently_enable_qpe(monkeypatch,tmp_path):
    path=tmp_path/'review.json';monkeypatch.setattr('sys.argv',['inspect','--export',str(path)])
    monkeypatch.setattr(review,'prefix',lambda url:header() if url.endswith('.nc') else b'ncols 1\nnrows 1\nxllcorner 95\nyllcorner 4\ncellsize .01\nNODATA_value -9999\n')
    review.main();value=json.loads(path.read_text())
    assert value['sources']['composite.nc']['nonplaceholder_units_supplied']
    assert value['state']=='NOT_ACCEPTED' and not value['publishes_grid']
