"""Measure the live SP range at private ABI entrances in opening 1..120."""
from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(RUNTIME.parent/'arm-registers/checkpoint.S').read_text()
k='\tadrp\tx2, ngb_reg_entries';assert s.count(k)==1
s=s.replace(k,''' adrp x1,domain_active
 ldr w1,[x1,:lo12:domain_active]
 cbz w1,.Ldomain_done
 lsr w1,w22,#12
 cmp w1,#0x4000
 b.lo .Ldomain_low
 mov w1,#0x4000
.Ldomain_low:
 adrp x2,domain_bank
 add x2,x2,:lo12:domain_bank
 ldr x3,[x2,x1,lsl #3]
 add x3,x3,#1
 str x3,[x2,x1,lsl #3]
.Ldomain_done:
'''+k)
f=p.out/'domain.S';f.write_text(s);o=f.with_suffix('.o')
subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'checkpoint.o'))]=str(o)
p.driver(r'''
unsigned domain_active;uint64_t domain_bank[16385];
void domain_flip(unsigned f){
 if(f==120)for(unsigned i=0;i<16385;i++)if(domain_bank[i])fprintf(stderr,"[SP_PAGE] %03x %llu\n",i,(unsigned long long)domain_bank[i]);
 domain_active=f<120;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void domain_flip(unsigned);domain_flip({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
