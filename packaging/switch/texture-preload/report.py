"""Compare identical render-frame endpoints; host times are not Switch times."""
from pathlib import Path
import re,sys
d=Path(sys.argv[1])
for scene in ('wide',):
    arms=[]
    for arm in ('off','on'):
        log=(d/(scene+'-'+arm+'.log')).read_text()
        assert 'reason=verified '+('120 original demo frames' if scene=='wide' else 'first chapter player control') in log
        rows={}
        # May get multiple renderer lifetimes: keep runs separate.
        life=-1;prev=0
        for tag,line in re.findall(r'\[(TEX_FIRST_USE|TEX_PRELOAD)\] ([^\n]+)',log):
            fields={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
            f=fields['frame']
            if tag=='TEX_FIRST_USE' and (life<0 or f<=prev):life+=1
            rows.setdefault((life,f),{}).update(fields)
            prev=f
        assert rows and all(r['enabled']==(arm=='on') for r in rows.values())
        arms.append(rows)
    for epoch in sorted(set(k[0] for k in arms[0])&set(k[0] for k in arms[1])):
        shared=sorted(k for k in arms[0].keys()&arms[1].keys() if k[0]==epoch)
        for k in sorted(set([shared[0],shared[-1]])):
            a,b=(r[k] for r in arms);print(f'{scene} epoch={epoch} frame={k[1]}: off/on misses {a["misses"]}/{b["misses"]}; preload hits {b["hits"]}; prepared at title {b["title"]}; cumulative foreground upload recording {a["upload_us_total"]/1000:.2f}/{b["upload_us_total"]/1000:.2f} ms; worst single frame foreground upload recording {a["worst_upload_us"]/1000:.2f}/{b["worst_upload_us"]/1000:.2f} ms.')
