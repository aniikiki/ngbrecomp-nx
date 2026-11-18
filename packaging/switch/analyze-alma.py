"""Summarize the last recorded Alma session; do not equate elapsed and CPU times."""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

def load(path):
    schemas, rows, lost, partial = {}, defaultdict(list), Counter(), 0
    for line in csv.reader(Path(path).open()):
        if not line:
            continue
        k, *v = line
        if k == '#SESSION':
            rows.clear(); schemas.clear(); lost.clear(); partial = 0
        elif k == '#LOST':
            lost[v[0]] += int(v[1])
        elif k.startswith('#'):
            schemas[k[1:]] = v
        elif k in schemas:
            if len(schemas[k]) != len(v) or not all(x.isdecimal() for x in v):
                partial += 1
                continue
            rows[k].append(dict(zip(schemas[k], map(int, v))))
    return rows, lost, partial

def report(path):
    rows, lost, partial = load(path)
    print('records', {k:len(v) for k,v in rows.items()}, 'dropped',dict(lost),'partial',partial)
    byframe=defaultdict(list)
    for q in rows['Q']:
        byframe[q['submit_frame']].append(q)
    guest=rows['G']
    if not guest or not rows['R']:
        print('No matched mission frames in last session');return
    origin=guest[0]['time_us']
    guests=defaultdict(list)
    for a,b in zip(guest,guest[1:]):
        if b['active'] and a['active'] and b['guest_flip']==a['guest_flip']+1:
            guests[(b['time_us']-origin)//1000000].append((a,b))
    renders=defaultdict(list)
    for r in rows['R']:renders[(r['time_us']-origin)//1000000].append(r)
    print('second hp frames guest_interval_ms guest_cpu_ms render_draws gpu_ms gpu_coverage compile_ms_sum texture_ms_sum')
    for t, pairs in sorted(guests.items()):
        rs=renders[t]
        if not rs:continue
        clocks=[(b['cpu_us']-a['cpu_us'])/1000 for a,b in pairs if 0<a['cpu_us']<=b['cpu_us']]
        costs=[]
        for r in rs:
            qs=byframe.get(r['present'],[])
            if qs and all(q['valid'] for q in qs):costs.append(sum(q['gpu_us'] for q in qs)/1000)
        print(t,pairs[-1][1]['hp'],len(pairs),
              round(mean((b['time_us']-a['time_us'])/1000 for a,b in pairs),2),
              round(mean(clocks),2) if clocks else 'NA',round(mean(r['drawn'] for r in rs)),
              round(mean(costs),2) if costs else 'NA',f'{len(costs)}/{len(rs)}',
              round(sum(r['compile_us'] for r in rs)/1000,2),
              round(sum(r['texture_us'] for r in rs)/1000,2))
    for r in rows['C'][-1:]:print('clock Hz and service status:',r)
    for side in (0,1):
        pcs=[p for p in rows['P'] if p['renderer']==side and not p['rc'] and p['pc_offset']!=0xffffffff]
        if pcs:print(('guest','render')[side],'sampled PC offsets:',[(hex(k),n) for k,n in Counter(p['pc_offset'] for p in pcs).most_common(6)])
    if rows['D']:
        print('display median us:',{k:median(d[k] for d in rows['D']) for k in ('acquire_us','blit_overlay_us','submit_us')})

if __name__=='__main__':report(sys.argv[1])
