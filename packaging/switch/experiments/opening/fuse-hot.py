"""Inline directly called short game routines at observed opening callers, even
across original XBE compilation units. Retain original public entries, poll
points, push/ret effects, unknown calls and memory checks. Generate locally."""
import sys,re,collections,os
from pathlib import Path
home=Path.cwd();base=home/'build/switch-runtime';abi=home/'packaging/switch/arm-registers'
units=(0,1,2,3,9,10,11,14,16,27,28,29,37,44)
counts=collections.Counter()
for f,s in re.findall(r'^\[ENTRY_MIX\] (\d+) (.*)$',(base/'core-perf/opening-setup/entry-mix.log').read_text(),re.M):
 if 31<=int(f)<=120:
  for va,n in re.findall(r'([a-f0-9]+):(\d+)',s):counts['sub_'+va.zfill(8).upper()]+=int(n)
fn=re.compile(r'^void (sub_[0-9A-F]+)\(void\)\n\{.*?^\}',re.M|re.S)
call=re.compile(r'RECOMP_ABI_CALL\((0x[0-9A-F]+u), (sub_[0-9A-F]+)\)')
src={u:(base/'gen'/f'recomp_{u:04}.c').read_text() for u in units}
bodies={m[1]:m[0] for s in src.values() for m in fn.finditer(s)}
copies=0;sites=0;targets=set()
d=base/'core-perf/opening-fuse-hot';d.mkdir(exist_ok=True)
for u,s in src.items():
 clones={}
 def caller(m):
  if counts[m[1]]<90:return m[0]
  def redirect(v):
   global sites
   name=v[2];b=bodies.get(name)
   if not b or name==m[1] or counts[name]<900 or len(b)>3400:return v[0]
   # Retain code interposition for anything with a custom source-level hook;
   # exclude local macro definitions and jump tables with label addresses.
   if '#' in b or '&&loc_' in b or 'static ' in b or '__func__' in b or 'goto *' in b:return v[0]
   if b.count(name)>1:return v[0]
   clones[name]=b.replace('void '+name+'(void)','static inline __attribute__((always_inline)) void fuse_'+name+'(void)',1)
   targets.add(name);sites+=1;return v[0].replace(name,'fuse_'+name)
  return call.sub(redirect,m[0])
 s=fn.sub(caller,s)
 pos=re.search(r'^void (?:sub_|d3d_orig_)\w+\(void\)\n\{',s,re.M)
 assert pos
 copies+=len(clones)
 if '--scan' not in sys.argv:(d/f'recomp_{u:04}.c').write_text(s[:pos.start()]+'\n'.join(clones.values())+'\n'+s[pos.start():])
print('explicit inline: distinct callees',len(targets),'copies',copies,'direct sites',sites,flush=True)
if '--scan' in sys.argv:sys.exit()
os.environ['NGB_REG_OUT']=str(d)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k,' c[-1]=str(o/n)\n'+k)
exec(compile(s,'fuse-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'fuse-gates','exec'),{})
for pat in ('recomp_*.s','recomp_*.c'):
 for f in d.glob(pat):f.unlink()
