"""Follow the active opening trials on the host, including after disconnect.
Writes only a small, replace-in-place report. Never label host timing device FPS."""
import argparse, json, os, re, time
from pathlib import Path
from statistics import mean
d=Path('build/switch-runtime/core-perf/wide-start')
tags=('vector-registers','live-matrices','double-entry','hle-leaf','full-guest','owner-recorder')
def outcome(tag):
    pairs=[];valid=0; errors=[]
    for i in range(1,5):
        halves=[]
        for arm in ('original','limit'):
            f=d/f'{tag}-{arm}-{i}.log'
            if not f.exists():continue
            s=f.read_text(errors='replace')
            if '[RESULT] status=1 reason=verified 120 original demo frames' not in s:continue
            rows=[tuple(map(int,r)) for r in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
            if [r[0] for r in rows]!=list(range(1,121)):continue
            valid+=1; halves.append([sum(x[k] for x in rows[j:]) for j in (0,30) for k in (1,2)])
        if len(halves)==2:
            a,b=halves
            pairs.append([round(1-b[j]/a[j],5) if j%2==0 else round(b[j]/a[j],5) for j in range(4)])
    for f in d.glob(tag+'-*.txt'):
        for line in f.read_text(errors='replace').splitlines():
            if 'error:' in line or 'Error:' in line or 'Traceback (' in line:errors.append(line[:300])
    r={'valid_runs':valid,'pairs':pairs}
    if errors:r['errors']=errors[-3:]
    if len(pairs)==4:r['mean_host_cpu_saved_fraction']=[round(mean(p[j] for p in pairs),5) for j in (0,2)]
    return r
def report():
    body=json.dumps({k:outcome(k) for k in tags},indent=2)+'\n'
    f=d/'follow-results.json'
    if not f.exists() or f.read_text()!=body:
        tmp=f.with_suffix('.tmp');tmp.write_text(body);os.replace(tmp,f)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--until-pid',type=int);a=ap.parse_args()
    while True:
        report()
        if not a.until_pid:break
        try: os.kill(a.until_pid,0)
        except ProcessLookupError:report();break
        time.sleep(20)
