"""Compare guest timing with older Switch stack counts; never scale one by the other."""
from pathlib import Path
from collections import Counter
import re, runpy, json, sys
inner="--inner" in sys.argv
name,unit,fn,size=("task2ae-cost",1,"0002AEB0",25) if "--update" in sys.argv else ("task200-cost",0,"00020040",26) if inner else ("task298-cost",1,"000298F0",12)
root=Path('build/switch-runtime')
h=root/'history/0.51.0-rc1'
api=runpy.run_path('packaging/switch/analyze-profile.py')
sym=api['load_symbols'](h/'symbols.gz')
device=(root/json.loads((h/'deployment.json').read_text())['hardware_log']).read_text()
samples=api['parse_windows'](device.splitlines())[1,120]['profiles']['guest'][1]
host=(root/f'core-perf/opening-{name}/budget.log').read_text()
assert 'reason=verified 120 original demo frames' in host
body=(root/f'gen/recomp_{unit:04}.c').read_text().split('void sub_'+fn+'(void)\n{')[1].split('\n}')[0]
sites=re.findall(r'PUSH32\(esp, 0x(\w+)u\); RECOMP_ABI_CALL\(0x(\w+)u',body)
assert len(sites)==size
for end,lo in ((30,1),(120,31)):
    device_counts=Counter()
    for frame,*_,pcs in samples:
        if not lo<=frame<=end:continue
        ids=[m[1] for pc in pcs if (m:=re.search(r'(?:sub|orig)_([0-9A-F]{8})(?:\b|_)',sym(pc)))]
        if '0030BCA0' in ids or fn not in ids: continue
        i=ids.index(fn); device_counts[ids[i-1] if i else 'self']+=1
    print('device window',lo,end,device_counts)
    rows=[tuple(map(int,m)) for m in re.findall(r'^\[TREE_COST\] '+str(end)+r' (\d+) calls=(\d+) samples=(\d+) ns=(\d+) blanks=(\d+) blank_ns=(\d+) cross=(\d+)$',host,re.M)]
    assert [r[0] for r in rows]==list(range(size))
    for i,c,n,t,b,z,x in sorted(rows,key=lambda r:r[3]-r[5],reverse=True):
        assert c==b and n+x==c
        if c:print(sites[i],c,'calls',x,'cross',round((t-z)/(end-lo+1)/1e3,2) if not x else None,'host us/frame')

    if name == "task2ae-cost":
        # A different, untimed replay. Check attribution at the measured boundary,
        # without treating deeper entries as time to add to the inclusive scope.
        census=(root/'core-perf/opening-guest-sites/budget.log').read_text()
        assert 'verified 120 original demo frames' in census
        visits={r:int(n) for r,n in re.findall(r'^\[GUEST_SITE\] '+str(end)+r' (\w+) 15fb0 (\d+)$',census,re.M)}
        site=sites.index(('0002AF7C','00015FB0'))
        print('15FB0 calls at 2AF7C (timed/independent), other callers (independent):',
              rows[site][1], visits['2af7c'], sum(visits.values())-visits['2af7c'])
