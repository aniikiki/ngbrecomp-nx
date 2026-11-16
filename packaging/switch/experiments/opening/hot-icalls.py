"""Opening-specific guarded direct calls. A training pass records guest site and
target, never host addresses. Keep trace, original call ABI and fallback for
any unseen target. No changes to invalid target or manual/kernel handling."""
from pathlib import Path
import os,re,sys,collections
base=Path('/work/build/switch-runtime');abi=Path('/work/packaging/switch/arm-registers')
train='--train' in sys.argv
d=base/'core-perf'/('opening-icall-train' if train else 'opening-icall-direct')
d.mkdir(exist_ok=True);os.environ['NGB_REG_OUT']=str(d)
units=(0,1,2,3,9,10,11,14,16,27,28,29,37,44)
symbols={int(a,16):'sub_'+a for a in re.findall(r'^\.global sub_([0-9A-F]+)$',(base/'native-regs/entry.S').read_text(),re.M)}
# Only specialize the exact implementation chosen by the dispatch table.
dispatch_rows=re.findall(r'\{\s*0x([0-9A-Fa-f]+)u,\s*\(recomp_func_t\)(\w+)\s*\}',(base/'gen/recomp_dispatch.c').read_text())
assert len(dispatch_rows)>10000
dispatch={int(va,16):name for va,name in dispatch_rows}
assert len(dispatch)==len(dispatch_rows)
symbols={va:name for va,name in symbols.items() if dispatch.get(va)==name}
assert 'recomp_lookup_manual(uint32_t va) { (void)va; return NULL; }' in (abi.parent/'runtime/runtime.c').read_text()
targets=collections.defaultdict(collections.Counter)
if not train:
 log=(base/'core-perf/wide-start/icall-training.log').read_text()
 assert '[RESULT] status=1 reason=verified 120 original demo frames' in log
 for site,va,n in re.findall(r'^\[ICALL_OPEN\] ([0-9a-f]+) ([0-9a-f]+) (\d+)$',log,re.M):
  targets[int(site,16)][int(va,16)]+=int(n)
 assert targets
nsite=0;count=0
for u in units:
 name=f'recomp_{u:04}.c';s=(base/'gen'/name).read_text()
 def repl(m):
  global nsite,count
  site=int(m[1],16)
  if train:return f'icall_open({m[1]}u,_icall_target); '+m[0]
  counts=targets[site];hits=[(v,n) for v,n in counts.most_common(2) if v in symbols and n>=100 and n*8>=sum(counts.values())]
  if not hits:return m[0]
  nsite+=1;count+=sum(n for v,n in hits)
  arms=''
  for v,n in hits:
   arms+=f'if(_icall_target==0x{v:08x}u && RECOMP_ICALL_IS_CODE(0x{v:08x}u)){{g_icall_trace[g_icall_trace_idx & (ICALL_TRACE_SIZE-1)]=_icall_target;++g_icall_trace_idx;++g_icall_count;RECOMP_ICALL_OBSERVE_SITE({m[1]}u,_icall_target);RECOMP_ICALL_OBSERVE(_icall_target,RECOMP_ICALL_SEEN_RESOLVED);RECOMP_ABI_CALL(0x{v:08x}u,{symbols[v]});}}else '
  return arms+m[0]
 s=re.sub(r'RECOMP_ICALL_SAFE_AT\(_icall_target, _icall_esp, (0x[0-9A-Fa-f]+)u\);',repl,s)
 if train:s='extern void icall_open(unsigned,unsigned);\n'+s
 (d/name).write_text(s)
if not train: print('guarded sites',nsite,'training hits',count,flush=True)
s=(abi/'compile.py').read_text();k=' sp.run(c,cwd=w,check=True)';assert s.count(k)==1
s=s.replace(k," c[-1]=str(o/n)\n"+k)
exec(compile(s,'icall-abi','exec'),{})
exec(compile((abi/'gates.py').read_text(),'icall-gates','exec'),{})
for f in d.glob('recomp_*.s'):f.unlink()
for f in d.glob('recomp_*.c'):f.unlink()
