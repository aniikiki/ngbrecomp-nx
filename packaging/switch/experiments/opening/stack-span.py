"""Opening trial: prove one 28-byte stack span instead of six word mappings in 3AE90."""
from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import NativeProbe,REGS,RUNTIME
p=NativeProbe('opening-setup')
f=REGS/'recomp_0002.c.gated.s';s=f.read_text()
a=s.index('\tsub\tw0, w22, #4',s.index('ngb_reg_sub_0003AE90:'))
z=s.index('\tcbz\tw3, .L371',a)
orig=s[a:z]
assert orig.count('ldrh')==6 and orig.count('bcc')==6
# Live scratch, NZCV, guest stack stores (including dead slots), and their order
# agree on a full ordinary page. Last read is at initial SP+8 (4 bytes).
s=s[:a]+''' adrp x16,span_arm
 ldr w16,[x16,:lo12:span_arm]
 cbz w16, .Lspan_base
 sub w0,w22,#16
 and w1,w0,#4095
 cmp w1,#4068
 b.hi .Lspan_base
 lsr w5,w0,#12
 ldrh w5,[x27,x5,lsl #1]
 cmp w5,#4096
 b.ne .Lspan_base
 and x0,x0,#0x7fffffff
 add x0,x26,x0
 str w4,[x0,#12]
 ldr w23,[x0,#24]
 str w3,[x0,#8]
 str w24,[x0,#4]
 ldr w24,[x0,#20]
 sub w22,w22,#16
 add w19,w19,4808704
 add w19,w19,2224
 mov w3,w21
 mov w4,w25
 str w4,[x0]
 add w1,w1,4
 cmp w5,w1
 b .Lspan_done
.Lspan_base:
'''+orig+'.Lspan_done:\n'+s[z:]
if '--check' in sys.argv:
    # Exercise the exact machine-code fragments above. Both arms use the same
    # RAM base so the computed host pointer, NZCV and scratch registers compare.
    import re
    d=p.out
    test='.text\n'
    for name,body in [('base',orig),('alt',s[a:s.index('.Lspan_base:',a)])]:
        body=re.sub(r'(?m)^\s*bcc\s+\.L\d+', ' b.lo 8f',body)
        body=body.replace('.Lspan_base','8f').replace('.Lspan_done','9f')
        test+=f'.global check_{name}\ncheck_{name}:\n'+"""
 sub sp,sp,#96
 stp x19,x20,[sp];stp x21,x22,[sp,#16];stp x23,x24,[sp,#32]
 stp x25,x26,[sp,#48];stp x27,x28,[sp,#64];str x0,[sp,#80]
 mov x26,x1;mov x27,x2
 ldr w3,[x0];ldr w4,[x0,#4];ldr w19,[x0,#8];ldr w21,[x0,#12];ldr w22,[x0,#16]
 ldr w23,[x0,#20];ldr w24,[x0,#24];ldr w25,[x0,#28]
 """+body+"""
9: ldr x6,[sp,#80]
 stp w3,w4,[x6];stp w19,w21,[x6,#8];stp w22,w23,[x6,#16];stp w24,w25,[x6,#24]
 stp x0,x1,[x6,#32];str x5,[x6,#48];mrs x1,nzcv;str x1,[x6,#56];mov w0,#1
 b 7f
8: mov w0,#0
7: ldp x19,x20,[sp];ldp x21,x22,[sp,#16];ldp x23,x24,[sp,#32]
 ldp x25,x26,[sp,#48];ldp x27,x28,[sp,#64];add sp,sp,#96;ret
"""
    (d/'span-check.S').write_text(test)
    c=Path(__file__).with_name('stack-span-check.c')
    exe=d/'span-check'
    subprocess.run(['cc','-O2',c,d/'span-check.S','-o',exe],check=True)
    subprocess.run([exe],check=True);sys.exit()
d=p.out;o=d/'stack-span.o';src=d/'stack-span.s';src.write_text(s)
subprocess.run(['cc','-c',src,'-o',o],check=True)
p.link[p.link.index(str(REGS/'recomp_0002.c.o'))]=str(o)
p.driver('''
unsigned span_arm;
void span_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned previous;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,span_arm,(unsigned long long)(now-last),draws-previous);
 span_arm=f<120 && ((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;previous=draws;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1
 s=s.replace(k,k+f' extern void span_frame(unsigned,unsigned);span_frame({arg},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
