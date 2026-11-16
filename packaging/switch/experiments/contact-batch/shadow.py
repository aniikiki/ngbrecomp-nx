from pathlib import Path
import subprocess as sp,shlex
r=Path('/work/build/switch-runtime');w=r/'switch';d=r/'opt050/contact-range'
n='recomp_0009.c';s=(r/'gen'/n).read_text()
tag='void sub_0013D330(void)\n{';assert s.count(tag)==1
s=s.replace(tag,Path(__file__).with_name('check.inc').read_text()+'\nextern void box_report(unsigned,unsigned,unsigned);\n'+tag+'\n    unsigned predicted=0;unsigned long long stamp=0;')
t='loc_0013D410: ; ngb_guest_block_poll();';assert s.count(t)==1
s=s.replace(t,t+' predicted=predict_box(ebx,esi);stamp=ngb_guest_polls;')
t='loc_0013D550: ;';assert s.count(t)==1;s=s.replace(t,t+' box_report(predicted,eax,(unsigned)(ngb_guest_polls-stamp));')
f=d/n;f.write_text(s);c=next(shlex.split(l) for l in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if l.endswith('/'+n));o=str(d/'shadow.o')
c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=w,check=True)
