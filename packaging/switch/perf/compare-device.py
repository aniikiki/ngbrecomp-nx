"""Compare matching full Switch profile windows without confusing game CPU with FPS."""
from pathlib import Path
import argparse, math, re, statistics
def load(path):
    text=Path(path).read_text(errors='replace')
    versions=re.findall(r'^\[BOOT\] NGB Switch startup adapter ([^;\s]+)',text,re.M)
    if len(versions)!=1:raise ValueError(f'{path}: expected one device boot')
    clocks={int(f):(int(c),int(g)) for f,c,g in re.findall(r'^\[CLOCK\] first=(\d+) cpu_hz=(\d+) gpu_hz=(\d+)',text,re.M)}
    rows={}
    for l in text.splitlines():
        if not l.startswith('[FRAME_CPU] '):continue
        d=dict(s.split('=',1) for s in l.split()[1:]);i=int(d['frame'])
        if i in rows:raise ValueError(f'{path}: duplicate frame {i}')
        row=tuple(int(d[k]) for k in ('wall_us','guest_cpu_us','draws'))+(int(d['rc'],16),)
        if row[0]<=0:raise ValueError(f'{path}: invalid frame time at {i}')
        rows[i]=row
    return versions[0],rows,clocks
def show(files):
    for a,b in [(1,120),(121,720),(721,840),(1801,1920)]:
        print(f'frames {a}-{b}')
        means=[];rates=[]
        for version,rows,clocks in files:
            w=[rows[i] for i in range(a,b+1) if i in rows]
            if len(w)!=b-a+1:
                print(f' {version}: incomplete ({len(w)}/{b-a+1}); no comparison');means.append(None);continue
            wall=sorted(x[0] for x in w);ms=statistics.mean(wall)/1000;means.append(ms)
            cpu=[x[1] for x in w if x[3]==0]
            c=f'{statistics.mean(cpu)/1000:.2f}' if len(cpu)==len(w) else f'unavailable ({len(cpu)}/{len(w)})'
            rate=clocks.get(a);rates.append(rate)
            clocks_msg=f'{rate[0]/1e6:g}/{rate[1]/1e6:g}' if rate and all(rate) else 'unknown'
            print(f' {version}: wall {ms:.2f} ms ({1000/ms:.2f} fps), P95 {wall[math.ceil(len(w)*.95)-1]/1000:.2f} ms, over-budget {sum(us*60>1000000 for us in wall)}/{len(w)}, guest CPU {c} ms, draws {statistics.mean(r[2] for r in w):.1f}, CPU/GPU MHz {clocks_msg}')
        if len(means)==2 and None not in means:
            print(f' wall time saved {means[0]-means[1]:+.2f} ms ({100*(1-means[1]/means[0]):+.1f}%); remaining vs 60 fps {means[1]-1000/60:+.2f} ms')
            if rates[0]!=rates[1] or not all(rates):print(' unmatched or missing clocks; do not attribute all of the change to the build')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline');p.add_argument('candidate',nargs='?');a=p.parse_args()
    show([load(f) for f in (a.baseline,a.candidate) if f])
