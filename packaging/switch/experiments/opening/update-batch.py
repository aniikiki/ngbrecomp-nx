"""Cross-check the previously shadow-tested grouped candidate implementation in the opening."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup');d=p.core/'compact-fast'
for src in sorted(REGS.glob('recomp_*.c.o'))+[REGS/'entry.o',REGS/'gates.o']:
 p.link.insert(1,str(d/('a-'+src.name)))
src=BASE/'opt050/contact-compact/recomp_0009.c.gated.s';code=src.read_text()
if '--why' in sys.argv:
 # Observe the real A-path, at the exact guard boundary, without changing arguments or NZCV.
 k='\tbl contact_group\n'
 assert code.count(k)==1
 inc=lambda n:f' adrp x16,batch_why\n add x16,x16,:lo12:batch_why\n ldr w17,[x16,#{4*n}]\n add w17,w17,#1\n str w17,[x16,#{4*n}]\n'
 trace=' mrs x15,nzcv\n'+inc(0)+"""
 adrp x16,batch_example
 add x16,x16,:lo12:batch_example
 stp w22,w23,[x16]
 str w24,[x16,#8]
 lsr w16,w22,#20
 cmp w16,#16
 b.lo 3f
 cmp w16,#62
 b.hs 3f
 """+inc(1)+"""
 sub w16,w22,#256
 and w16,w16,#4095
 cmp w16,#3696
 b.hi 3f
 """+inc(2)+"""
 mov w16,#0x79c6
 movk w16,#0x7a,lsl 16
 sub w16,w23,w16
 cmp w16,#2048
 b.hs 3f
 """+inc(3)+"""
 add x16,x26,w22,uxtw
 ldr w17,[x16,#28]
 sub w17,w17,w22
 cmp w17,#48
 b.ne 3f
 """+inc(4)+"""
3: msr nzcv,x15
 """
 # Diagnostic only: x15 may be live across this call under the private ABI.
 code=code.replace(k,' stp x15,x17,[sp,#-16]!\n'+trace+' ldp x15,x17,[sp],#16\n'+k)
for i,callee in enumerate(('contact_group','contact_leaf')):
 k='\tbl '+callee+'\n\tcbnz\tw0, .L69634';assert code.count(k)==1
 bump=f''' cbz w0,1f
 adrp x16,batch_hits
 add x16,x16,:lo12:batch_hits
 ldr w17,[x16,#{i*8}]
 add w17,w17,#1
 str w17,[x16,#{i*8}]
 ldr w17,[x16,#{i*8+4}]
 add w17,w17,w0
 str w17,[x16,#{i*8+4}]
1:
'''
 code=code.replace(k,'\tbl '+callee+'\n'+bump+'\tcbnz\tw0, .L69634')
asm=p.out/'candidate-hit.s';obj=p.out/'candidate-hit.o';asm.write_text(code)
subprocess.run(['cc','-c',asm,'-o',obj],check=True)
subprocess.run(['objcopy','--redefine-syms='+str(d/'a.map'),obj],check=True)
p.link[p.link.index(str(d/'a-recomp_0009.c.o'))]=str(obj)
f=REGS/'recomp_0009.c.gated.s';baseline=f.read_text()
k='ngb_reg_sub_0013D330:\n';assert baseline.count(k)==1
baseline=baseline.replace(k,k+' adrp x16,trial_variant\n ldr w16,[x16,:lo12:trial_variant]\n cbnz w16,a_ngb_reg_sub_0013D330\n')
# Use a long unconditional branch for a destination outside the cbnz reach.
baseline=baseline.replace(' cbnz w16,a_ngb_reg_sub_0013D330',' cbz w16,1f\n b a_ngb_reg_sub_0013D330\n1:')
asm=p.out/'candidate-base.s';obj=p.out/'candidate-base.o';asm.write_text(baseline)
subprocess.run(['cc','-c',asm,'-o',obj],check=True)
p.link[p.link.index(str(REGS/'recomp_0009.c.o'))]=str(obj)
p.link.insert(1,'-Wl,--strip-debug')
p.driver(r'''
unsigned trial_variant,batch_hits[4],batch_why[5],batch_example[3];
void batch_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,trial_variant,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[BATCH_WHY] %u %u %u %u %u sp=%x node=%x query=%x\n",batch_why[0],batch_why[1],batch_why[2],batch_why[3],batch_why[4],batch_example[0],batch_example[1],batch_example[2]);
 if(f==120)fprintf(stderr,"[BATCH_HITS] %u %u %u %u\n",batch_hits[0],batch_hits[1],batch_hits[2],batch_hits[3]);
 trial_variant=f<120 && ((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void batch_frame(unsigned,unsigned);batch_frame({arg},draws);')
p.add('scene/bridge.c',s);p.finish()
