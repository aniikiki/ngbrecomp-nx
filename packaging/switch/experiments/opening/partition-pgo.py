"""Keep rare blocks out of hot guest bodies using the already finalized, identical profile."""
from pathlib import Path
import os,subprocess,struct,sys
no_tracer="--no-tracer" in sys.argv
no_unroll="--no-unroll" in sys.argv
early_sched="--early-sched" in sys.argv
assert sum((early_sched,no_unroll,no_tracer))<=1
p=Path(__file__).resolve().parent
trained=Path('/work/build/switch-runtime/core-perf/opening-retained-pgo')
out=trained.parent/('opening-partition-early-sched' if early_sched else 'opening-partition-no-tracer' if no_tracer else 'opening-partition-no-unroll' if no_unroll else 'opening-partition-pgo');out.mkdir(exist_ok=True)
base=(p/'retained-pgo-build.py').read_text()
a=base.index('s=(abi/');b=base.index('if local:',a)
s=base[a:b]
names=[f'recomp_{u:04}.c' for u in (2,10,16,28,29)]
abi=p.parents[1]/'arm-registers';d=out
import re
os.environ.update(NGB_REG_PROFILE='use',NGB_REG_OUT=str(out))
exec(s)
key=' sp.run(c,cwd=w,check=True)'
assert s.count(key)==1
s=s.replace(key,""" trained=Path('/work/build/switch-runtime/core-perf/opening-retained-pgo')
 assert all((trained/h).read_bytes()==(o/h).read_bytes() for h in ('regs.h','guest_memory.h'))
 c[c.index('-I'+str(o))]='-I'+str(trained)
 c[c.index(str(header))]=str(trained/'regs.h')
 c[c.index('-fprofile-dir='+str(o/'profiles'))]='-fprofile-dir='+str(trained/'profiles')
 c[c.index('-fno-reorder-blocks-and-partition')]='-freorder-blocks-and-partition'
 tmp=trained/(n+'.native.s')
 assert not tmp.exists()
 c[c.index('-o')+1]=str(tmp)
 try:
  sp.run(c,cwd=w,check=True)
  tmp.rename(o/(n+'.native.s'))
 finally:tmp.unlink(missing_ok=True)
""")
if no_tracer or no_unroll or early_sched:
 flag="-fschedule-insns" if early_sched else "-fno-unroll-loops" if no_unroll else "-fno-tracer"
 key='  sp.run(c,cwd=w,check=True)'
 assert s.count(key)==1
 s=s.replace(key,f"  c.insert(-1,{flag!r})\n"+key)
exec(compile(s,'partition-guest','exec'),{})
exec(compile((abi/'gates.py').read_text(),'partition-gates','exec'),{})
nm='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm'
def syms(f):
 rows=subprocess.check_output([nm,'-S','--defined-only',f],text=True)
 return {v[3]:int(v[1],16) for line in rows.splitlines() if len(v:=line.split())==4 and v[2] in ('t','T')}
hotdelta=cold=0
for n in names:
 old=syms(trained/(n+'.o'));new=syms(out/(n+'.o'))
 a={k for k in old if k.startswith('ngb_reg_') and '.' not in k}
 b={k for k in new if k.startswith('ngb_reg_') and '.' not in k}
 assert a==b and len(a)==250
 delta=sum(old[k]-new[k] for k in a)
 tails=sum(v for k,v in new.items() if '.cold' in k)
 print(n,'primary guest symbols bytes removed',delta,'out-of-line cold symbol bytes',tails,flush=True)
 hotdelta+=delta;cold+=tails
for f in out.glob('recomp_*.s'):f.unlink()
assert hotdelta>0 and cold>0,'compiler did not shrink primary guest bodies by splitting cold blocks'
