"""Resolve stack return + callee against an unambiguous generated direct call site."""
import re
from pathlib import Path
from collections import Counter,defaultdict
base=Path('build/switch-runtime')
marks=defaultdict(set)
for src in sorted((base/'gen').glob('recomp_[0-9][0-9][0-9][0-9].c')):
    s=re.sub(r'#ifdef NGB_DIRECT3D\n(void d3d_orig_\w+\(void\))\n#else\nvoid sub_\w+\(void\)\n#endif',r'\1',src.read_text())
    for m in re.finditer(r'^void (?:sub_|d3d_orig_)([0-9A-F]+)\(void\)\n\{(.*?)^\}',s,re.M|re.S):
        for ret,va,dest in re.findall(r'PUSH32\(esp, 0x([0-9A-F]+)u\); RECOMP_ABI_CALL\(0x([0-9A-F]+)u, sub_([0-9A-F]+)\)',m[2]):
            if int(va,16)==int(dest,16):marks[int(ret,16),int(va,16)].add(int(m[1],16))
log=(base/'core-perf/opening-guest-sites/budget.log').read_text()
assert 'verified 120 original demo frames' in log
training=None
for f,vis,bad,drop in re.findall(r'^\[SITE_TOTAL\] (\d+) (\d+) (\d+) (\d+)$',log,re.M):
    sites=Counter();families=defaultdict(Counter);unassigned=0
    for a,b,n in re.findall(r'^\[GUEST_SITE\] '+f+r' (\w+) (\w+) (\d+)$',log,re.M):
        key=int(a,16),int(b,16);n=int(n)
        if len(marks[key])!=1:unassigned+=n;continue
        parent=next(iter(marks[key]))
        sites[parent,key[0],key[1]]+=n
        families[parent][key[1]]+=n
    assert sum(sites.values())+unassigned+int(bad)+int(drop)==int(vis)
    qualified={p:sum(c.values()) for p,c in families.items() if len(c)>=3}
    if training is None:training=sorted(qualified,key=qualified.get,reverse=True)[:10]
    print(f,'entries',vis,'unreadable',bad,'table drops',drop,'static direct-site matches',sum(sites.values()),'selected parents',sum(sum(families[p].values()) for p in training))
    for p in training:
        c=families[p]
        print(hex(p),sum(c.values()),'distinct children',len(c),'top',[(hex(v),n) for v,n in c.most_common(4)])
    # Independent earlier instrumentation that timed individual call sites.
    e=base/'core-perf/opening-task-edges'
    keys={int(k,16):(int(p,16),int(t.split('_')[-1],16)) for k,p,t in (line.split() for line in (e/'host/edges.txt').read_text().splitlines())}
    others=Counter()
    for k,n,ns in re.findall(r'^\[CB_COST\] '+f+r' (\w+) (\d+) (\d+)$',(e/'distribution.log').read_text(),re.M):
        if int(k,16) in keys:others[keys[int(k,16)]]+=int(n)
    compared=[(key,n,families[key[0]][key[1]]) for key,n in others.items() if n and families[key[0]][key[1]]]
    print('overlapping independently counted edges',len(compared),'exact',sum(x==y for _,x,y in compared),'counts old/new',sum(x for _,x,_ in compared),sum(y for _,_,y in compared))
