"""Compare game-thread CPU in alive mission-23 frames with comparable draw counts.

Independent replays are not deterministic or a Switch FPS forecast. Report the
selection and draw distribution, including all eligible combat frames.
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('control',type=Path); p.add_argument('native',type=Path); p.add_argument('--output',type=Path)
args=p.parse_args()
def load(path):
    assert json.loads((path/'result.json').read_text())['passed'],path
    return [r for r in csv.DictReader((path/'frames.csv').open()) if r.get('cpu_ns') and
            r['mission']=='23' and r['mode']=='3' and r['max_hp']=='2400' and int(r['hp'])>0 and int(r['draw_apis'])>=250]
def stats(rows,lo,hi):
    r=[a for a in rows if lo<=int(a['draw_apis'])<hi]
    v=sorted(int(a['cpu_ns'])/1e6 for a in r)
    assert len(v)>=30,(lo,hi,len(v))
    return {'frames':len(v),'mean_cpu_ms':statistics.mean(v),'p50_cpu_ms':statistics.median(v),
            'p95_cpu_ms':v[min(len(v)-1,int(len(v)*.95))],
            'mean_draw_apis':statistics.mean(int(a['draw_apis']) for a in r)}
a,b=load(args.control),load(args.native)
report={'control':str(args.control),'native':str(args.native),'windows':{},
        'caveat':'Host ARM game-thread CPU, including guest worker scheduling/waits; independent inputs are not a deterministic capture replay. No Switch performance inference.'}
for label,lo,hi in [('all_alive_combat',250,100000),('450_to_549_draw_apis',450,550)]:
    c,n=stats(a,lo,hi),stats(b,lo,hi)
    report['windows'][label]={'control':c,'native':n,'cpu_change_percent':100*(n['mean_cpu_ms']/c['mean_cpu_ms']-1)}
text=json.dumps(report,indent=2)+'\n'
if args.output:args.output.write_text(text)
print(text)
