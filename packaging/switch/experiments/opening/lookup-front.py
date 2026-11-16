"""Immutable 256-slot front table; exact-key miss falls through to original dispatch."""
from pathlib import Path
import re,shlex,subprocess as sp
def install(p):
 base=p.core.parent;gen=base/'gen/recomp_dispatch.c';s=gen.read_text()
 rows={int(k,16):v for k,v in re.findall(r'\{\s*0x([0-9A-Fa-f]+)u,\s*\(recomp_func_t\)(\w+)\s*\}',s)}
 log=(p.core/'opening-lookup-mix/budget.log').read_text();assert 'verified 120 original demo frames' in log
 freq={}
 for k,n in re.findall(r'^\[LOOKUP_KEY\] (?:30|120) (\w+) (\d+)$',log,re.M):
  k=int(k,16);freq[k]=freq.get(k,0)+int(n)
 front={}
 for k in sorted(freq,key=lambda k:(-freq[k],k)):
  if k in rows and k:front.setdefault((k^(k>>8))&255,k)
 key='recomp_func_t recomp_lookup(uint32_t xbox_va)\n{'
 assert s.count(key)==1 and s.count('if (xbox_va - g_flat_base >= g_flat_span) return NULL;')==1
 table='static const recomp_entry_t opening_front[256]={\n'+''.join(f'[{i}]={{0x{k:x}u,(recomp_func_t){rows[k]}}},\n' for i,k in sorted(front.items()))+'};\n'
 s=s.replace(key,table+key).replace('unsigned slot = (xbox_va *','const recomp_entry_t *hit=&opening_front[(xbox_va^(xbox_va>>8))&255];\n    if(hit->xbox_va==xbox_va)return hit->func;\n    unsigned slot = (xbox_va *',1)
 w=base/'switch';cmds=sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines()
 cmd,=[shlex.split(l) for l in cmds if l.endswith('/recomp_dispatch.c')]
 f=p.out/'lookup-front.c';obj=f.with_suffix('.o');f.write_text(s)
 cmd[cmd.index('-o')+1]=str(obj);cmd[cmd.index('-MF')+1]=str(obj)+'.d';cmd[-1]=str(f);cmd.insert(1,'-I'+str(gen.parent));sp.run(cmd,cwd=w,check=True)
 old,=[v for v in p.link if v.endswith('/recomp_dispatch.o')];p.link[p.link.index(old)]=str(obj)
 print('immutable dispatch slots',len(front),'training eligible hits',sum(freq[k] for k in front.values()),flush=True)
