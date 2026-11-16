"""Package a wide 0.55.5-compatible memory experiment in an isolated directory,
only if four sequential, order-balanced full opening run pairs show a repeatable
improvement on the host. This never deploys or reports a device FPS."""
from pathlib import Path
import re,statistics as st,sys
root=Path('/work');base=root/'build/switch-runtime';w=base/'core-perf/wide-start'
def scores(tag):
 a=[]
 for i in range(1,5):
  both=[]
  for arm in ('original','limit'):
   s=(w/f'{tag}-{arm}-{i}.log').read_text()
   assert '[RESULT] status=1 reason=verified 120 original demo frames' in s
   v=[tuple(map(int,m)) for m in re.findall(r'^\[OPEN_PAIR\] (\d+) \d+ (\d+) (\d+)$',s,re.M)]
   assert [x[0] for x in v]==list(range(1,121))
   both.append((st.mean(x[1] for x in v[30:])/1e6,st.mean(x[2] for x in v[30:])))
  a.append((both[0][0]-both[1][0],both[1][1]/both[0][1]))
 return a
ok=[]
compile_only='--compile-only' in sys.argv
for tag in (v for v in sys.argv[1:] if v!='--compile-only'):
 pairs=scores(tag);gain=st.mean(x[0] for x in pairs)
 print(tag,'host-only savings ms and work ratios',pairs,flush=True)
 if (compile_only or gain>=0.15) and min(x[0] for x in pairs)>0 and all(.96<x[1]<1.04 for x in pairs):ok.append((gain,tag))
if not ok:
 print('No candidate cleared the host evidence threshold. No NRO produced.');sys.exit(0)
if compile_only:print('Local compile check only; not qualified for deployment.',flush=True)
tag=max(ok)[1]; d=base/'core-perf'/('opening-image-literals' if tag=='literals' else 'opening-page-limit')
version='0.55.6-'+('image' if tag=='literals' else 'page')
p=Path(__file__).with_name('submit-bound-device.py');s=p.read_text()
def once(k,v):
 global s
 assert s.count(k)==1,k
 s=s.replace(k,v)
once("out=base/'history'/version;",f"version='{version}';out=base/'history'/version;")
k=" regs=sorted(reg.glob('recomp_*.c.o'))"
services=(" comp('vm.c',(alt/'vm.c').read_text())\n comp('contiguous.c',(alt/'contiguous.c').read_text())\n" if tag=='page-limit' else
" comp('timers.c',(root/'timers.c').read_text()+'\\nvoid ngb_literal_no_ram(void){__builtin_trap();}\\n')\n")
once(k," alt=Path("+repr(str(d))+")\n"+services+k.replace("reg.glob","alt.glob"))
once("str(reg/(k+'.o'))","str((alt if k in ('entry','gates') else reg)/(k+'.o'))")
sys.argv=[str(p),'--wide','--pad','--movie','--save','--cg','--hold']
exec(compile(s,str(p),'exec'),{'__name__':'__main__'})
