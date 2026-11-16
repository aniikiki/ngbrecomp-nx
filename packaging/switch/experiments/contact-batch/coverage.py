"""Count actual failures at each precondition. Standalone original, no skipping."""
from pathlib import Path
import shlex,subprocess as sp
p=Path('/work/build/switch-runtime');d=p/'opt050/contact-coverage';d.mkdir(exist_ok=True);w=p/'switch';name='recomp_0009.c'
s=(p/'gen'/name).read_text();k='loc_0013D410: ; ngb_guest_block_poll();'
assert s.count(k)==1
s=s.replace(k,k+'''
    {static unsigned long counts[10],calls;static unsigned seen[16];
    uint32_t sp_=esp,i_=MEM32(sp_+24),n_=MEM32(0xbbba28),ball_=MEM32(esi);
    unsigned test[]={ngb_ram_span(sp_-256,400)!=0, !ngb_pending_dpcs,
      i_<n_ && n_<=256, ebx==0x7a79c6u+8*i_, MEM32(sp_+28)==sp_+48,
      (ngb_poll_mask-(ngb_guest_polls&ngb_poll_mask)+1)/7>=2,n_-i_>=2,
      esi>=0x8000 && esi<0x1000000-40,(ball_>=0x1000000 && ball_<0x3e00000)};
    for(unsigned g=0;g<9;g++)counts[g]+=test[g];
    unsigned g=0;while(g<9 && test[g])g++;++seen[g];
    if(!(++calls%32768)){
      extern void leaf_log(const char*,...);
      leaf_log("[COVER] n=%u sp=%x i=%u end=%u node=%x owner=%x ball=%x guard=%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu first=%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\\n",calls,sp_,i_,n_,ebx,esi,ball_,counts[0],counts[1],counts[2],counts[3],counts[4],counts[5],counts[6],counts[7],counts[8],seen[0],seen[1],seen[2],seen[3],seen[4],seen[5],seen[6],seen[7],seen[8],seen[9]);
    }}
''')
f=d/name;f.write_text(s);c=next(shlex.split(l) for l in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if l.endswith('/'+name))
o=str(d/'shadow.o');c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=w,check=True)
