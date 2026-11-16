"""Switch link/package check only. Reuse the tested 47 full-page objects,
matching VM writers and bridges, retain 0.55.5 input/save/movie behavior.
Never deploy; refuses incomplete or non-positive natural opening A/B pairs."""
from pathlib import Path
import runpy,sys
p=Path(__file__).resolve().parent;d=Path('/work/build/switch-runtime/core-perf/opening-full-page')
r=runpy.run_path(str(p/'follow-results.py'))['outcome']('full-page')
assert r['valid_runs']==8 and not r.get('errors'),r
assert len(r['pairs'])==4 and all(x[0]>0 and x[2]>0 and .96<x[1]<1.04 and .96<x[3]<1.04 for x in r['pairs']),r
s=(p/'submit-bound-device.py').read_text()
def once(k,v):
 global s
 assert s.count(k)==1,k
 s=s.replace(k,v)
once("out=base/'history'/version;","version='0.55.6-fullpage';out=base/'history'/version;")
k=" regs=sorted(reg.glob('recomp_*.c.o'));assert len(regs)==14"
once(k,f" alt=Path({str(d)!r})\n for nm in ('vm.c','contiguous.c'):comp(nm,(alt/nm).read_text())\n regs=sorted(alt.glob('recomp_*.c.o'));assert len(regs)==47")
once("str(reg/(k+'.o'))","str((alt if k in ('entry','gates') else reg)/(k+'.o'))")
once("assert b' bd_ticks\\n' in nm","assert all(k in nm for k in (b' bd_ticks\\n',b' opening_end4\\n',b' ngb_reg_xbe_entry_point\\n'))")
sys.argv=['submit-bound-device.py','--wide','--pad','--movie','--save','--cg','--hold']
exec(compile(s,str(p/'submit-bound-device.py'),'exec'),{'__name__':'__main__'})
