"""Replace side-effect-bounded branches of 3AE90 after the original guest checkpoint."""
from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup');fused='--fused' in sys.argv
if fused:p.out=p.core/'predicate-fused';p.out.mkdir(exist_ok=True)
s=(REGS/'recomp_0002.c.gated.s').read_text()
name='ngb_reg_sub_'+('0003B420' if fused else '0003AE90');k=name+':';a=s.index(k);b=s.index('\t.size\t'+name,a);body=s[a:b]
k='\tbl ngb_reg_checkpoint';assert body.count(k)==1
# Keep the verified path synchronous; the selected guest branches have no
# callbacks or polls after entry. Capture a marker on the native stack.
body=body.replace(k,k+'''
 adrp x0,pred_arm
 ldr w0,[x0,:lo12:pred_arm]
 cbz w0,.Lpn_orig
 mov x0,x26
 mov w1,w22
 mov w2,w20
 mov w3,w21
 mov w4,w23
 mov w5,w24
 mov w6,w25
 ldr w7,[x28,#36]
 bl pred_compute
 cbz x0,.Lpn_orig
 adrp x1,pred_arm
 ldr w1,[x1,:lo12:pred_arm]
 cmp w1,#1
 b.ne .Lpn_audit
 ldp w19,w20,[x0]
 ldr w21,[x0,#8]
 add w22,w22,#4
 ldp x29,x30,[sp],#32
 ret
.Lpn_audit:
 // Install audit return address in this function's saved LR slot.
 ldr x0,[sp,#8]
 adrp x1,pn_return
 str x0,[x1,:lo12:pn_return]
 adr x0,.Lpn_after
 str x0,[sp,#8]
.Lpn_orig:''')
s=s[:a]+body+s[b:]+'''
.text
.Lpn_after:
 mov w0,w22
 mov w1,w19
 mov w2,w20
 mov w3,w21
 mov w4,w23
 mov w5,w24
 mov w6,w25
 bl pred_check
 adrp x0,pn_return
 ldr x30,[x0,:lo12:pn_return]
 ret
'''
if fused:
 s=s.replace('bl pred_compute','adrp x8,pf_actor\n str w19,[x8,:lo12:pf_actor]\n bl pf_try').replace('bl pred_check','bl pf_check').replace('pred_arm','pf_arm')
f=p.out/'pred-native.s';o=f.with_suffix('.o');f.write_text(s);subprocess.run(['cc','-c',f,'-o',o],check=True)
p.link[p.link.index(str(REGS/'recomp_0002.c.o'))]=str(o)
pre=Path(__file__).with_name('predicate-fused.inc' if fused else 'predicate-native.inc').read_text();driver=r'''
uintptr_t pn_return;
void pn_flip(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,pred_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[PRED_NATIVE] %u %u\n",pn_hits,pn_checked);
 pred_arm=f>=120?0:getenv("NGB_PRED_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
'''
if fused:driver=driver.replace('pred_arm','pf_arm').replace('pn_hits','pf_hits').replace('pn_checked','pf_checks')
p.driver(pre+driver)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void pn_flip(unsigned,unsigned);pn_flip({arg},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
