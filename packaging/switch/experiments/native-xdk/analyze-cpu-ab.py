"""Compare alternating implementations inside one headless Alma battle.

Exclude detailed diagnostic frames. Pair adjacent frames by HP and draw count,
never by measured CPU time. This is not a prediction of Switch performance.
"""
import argparse
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
import random
from statistics import mean, median

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('report', type=Path)
args = p.parse_args()
assert json.loads((args.report / 'result.json').read_text())['passed']
spec = importlib.util.spec_from_file_location('diag', Path(__file__).with_name('analyze-diag.py'))
diag = importlib.util.module_from_spec(spec); spec.loader.exec_module(diag)
s = diag.load(args.report)[-1]; diag.verify(s)
native = {n['native_frame']: n for n in s['rows']['N']}
rows = [{k:int(v) for k,v in r.items()} for r in csv.DictReader((args.report / 'cpu-ab.csv').open())]
alive = []
for r in rows:
    if r['mission']!=23 or r['mode']!=3 or r['max_hp']!=2400 or not r['hp'] or r['draws']<250:
        continue
    n = native.get(r['frame']+1)
    assert n is not None and n['draws']==r['draws'], ('frame join mismatch', r, n)
    if n['profiled']: continue
    alive.append(dict(r, cpu_ms=n['frame_cpu_us']/1000))

def stats(rows):
    values=sorted(r['cpu_ms'] for r in rows)
    return dict(frames=len(rows),mean_cpu_ms=mean(values),p50_cpu_ms=median(values),
                p95_cpu_ms=values[int(len(values)*.95)],mean_draws=mean(r['draws'] for r in rows))

slow = [r for r in alive if not r['fast']]; fast = [r for r in alive if r['fast']]
assert min(len(slow),len(fast))>=50
used=set();pairs=[]
for a in fast:
    candidates=[b for b in slow if b['frame'] not in used and abs(a['frame']-b['frame'])<=8
                and a['hp']==b['hp'] and abs(a['draws']-b['draws'])<=4]
    if not candidates: continue
    b=min(candidates,key=lambda b:(abs(a['draws']-b['draws']),abs(a['frame']-b['frame']),b['frame']))
    used.add(b['frame']);pairs.append(dict(fast=a,control=b,saved_cpu_ms=b['cpu_ms']-a['cpu_ms']))
assert len(pairs)>=30, len(pairs)
blocks=defaultdict(list)
for v in pairs: blocks[min(v['fast']['frame'],v['control']['frame'])//32].append(v['saved_cpu_ms'])
blocks=list(blocks.values());rng=random.Random(573);boot=[]
for _ in range(5000):
    chosen=rng.choices(blocks,k=len(blocks));boot.append(mean(x for b in chosen for x in b))
boot.sort()
control=mean(v['control']['cpu_ms'] for v in pairs);optimized=mean(v['fast']['cpu_ms'] for v in pairs)
result=dict(control=stats(slow),optimized=stats(fast),pairs=len(pairs),blocks=len(blocks),
            paired_control_cpu_ms=control,paired_optimized_cpu_ms=optimized,
            paired_saved_cpu_ms=control-optimized,paired_change_percent=100*(optimized/control-1),
            paired_median_saved_cpu_ms=median(v['saved_cpu_ms'] for v in pairs),
            bootstrap_95_interval_saved_ms=[boot[125],boot[4875]],
            selection='Same battle, alive, >=250 draws, non-profiled; pairs <=8 frames apart, same HP, <=4 draw difference.',
            limitations='Adjacent frames are not identical game inputs. Block bootstrap describes this run only. Host CPU is not Switch FPS.')
(args.report/'cpu-ab-summary.json').write_text(json.dumps(result,indent=2)+'\n')
(args.report/'cpu-ab-pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
print(json.dumps(result,indent=2))
