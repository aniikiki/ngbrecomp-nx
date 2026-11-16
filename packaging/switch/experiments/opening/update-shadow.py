"""Replay compact candidate groups against all original candidates at opening only."""
from pathlib import Path
import shlex,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
out=BASE/'core-perf/opening-setup'
if sys.argv[1]=='cross':
 s=(BASE/'opt050/contact-compact/shadow.c').read_text()
 a=' if(!remain && ++calls%11==0';assert s.count(a)==1
 s='extern unsigned ubs_active,ubs_groups,ubs_items;\n'+s.replace(a,' if(ubs_active && !remain && ++calls%1==0')
 a='  groups[group_size]++;';assert s.count(a)==1;s=s.replace(a,'  ++ubs_groups;ubs_items+=group_size;'+a)
 f=out/'ubs.c';f.write_text(s)
 c=next(shlex.split(l) for l in subprocess.check_output(['ninja','-t','commands','ngb-startup'],cwd=BASE/'switch',text=True).splitlines() if l.endswith('/recomp_0009.c'))
 c[c.index('-o')+1]=str(out/'ubs.o');c[c.index('-MF')+1]=str(out/'ubs.d');c[-1]=str(f);c.insert(-1,'-g0');subprocess.run(c,cwd=BASE/'switch',check=True)
else:
 p=NativeProbe('opening-setup');p.driver(r'''
#include <stdarg.h>
unsigned ubs_active,ubs_groups,ubs_items;
void leaf_log(const char *fmt,...){va_list a;va_start(a,fmt);vfprintf(stderr,fmt,a);va_end(a);}
void ubs_frame(unsigned f){if(f==120)fprintf(stderr,"[OPEN_SHADOW] groups=%u items=%u\n",ubs_groups,ubs_items);ubs_active=f<120;}
''')
 orig=json.loads((p.core/'exact-link.json').read_text())
 for i,u in enumerate(p.link):
  if u.endswith('.c.o') and '/native-regs/recomp_' in u:
   n=Path(u).name.replace('.c.o','.o');p.link[i]=str(out/'ubs.o') if n=='recomp_0009.o' else next(t for t in orig if t.endswith('/'+n))
 for n in ('entry','gates'):p.link.remove(str(REGS/(n+'.o')))
 s=(RUNTIME/'scene/bridge.c').read_text()
 for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
  assert s.count(k)==1;s=s.replace(k,k+f' extern void ubs_frame(unsigned);ubs_frame({arg});')
 p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
