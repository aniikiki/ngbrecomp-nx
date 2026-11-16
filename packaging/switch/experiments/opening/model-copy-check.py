"""Use actual generated REP bodies and exercise the same guarded copy differential harness."""
from pathlib import Path
import runpy
p=Path(__file__).resolve().parent
m=runpy.run_path(str(p/'model-copy.py'))
pairs=set()
for u,vas in m['sites'].items():
 s=Path(f'build/switch-runtime/gen/recomp_{u:04}.c').read_text()
 t=m['transform'](s,u)
 for va in vas:
  bodies=[]
  for text,key in [(s,m['old']),(t,m['fast'])]:
   a=text.index(key,text.index('void sub_'+va+'(void)\n{'))
   bodies.append('ecx=16;edi=ebx;'+text[a:text.index('/* rep movsd */',a)])
  pairs.add(tuple(bodies))
assert len(pairs)==1
a,b=pairs.pop()
s=(p/'paired-copy-check.py').read_text()
s=s[s.index("code=r'''"):]
start=s.index("code+='static void ref");end=s.index("code+=r'''",start)
s=s[:start]+"code+='static void ref(void){'+a+'}\\nstatic void alt(void){'+b+'}\\n'\n"+s[end:]
s=s.replace('104','64').replace('paired-copy verified','seven model sites verified')
import tempfile,subprocess
exec(compile(s,'rep-check','exec'))
