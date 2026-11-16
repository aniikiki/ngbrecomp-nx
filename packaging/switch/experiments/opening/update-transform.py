"""Use direct NEON for 35A00's in-place triangle transform, after each original poll."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
# Compare mode must run on the --verify binary; a timing binary never checks its own output.
p=NativeProbe('opening-setup')
f=REGS/'recomp_0028.c.gated.s';s=f.read_text()
a=s.index('ngb_reg_sub_00305D60:');b=s.index('\t.size\tngb_reg_sub_00305D60',a)
body=s[a:b];k='.L1025:\n';assert body.count(k)==1
code="""
 adrp x15,ut_arm
 ldr w15,[x15,:lo12:ut_arm]
 cbz w15,.Lut_orig
 cmp w24,w21
 b.ne .Lut_orig
 mov w9,#0x4be0
 movk w9,#0x49,lsl 16
 sub w9,w24,w9
 cmp w9,#4048
 b.hi .Lut_orig
 tst w9,#15
 b.ne .Lut_orig
 lsr w9,w22,#20
 cmp w9,#16
 b.lo .Lut_orig
 cmp w9,#62
 b.hs .Lut_orig
 and w9,w22,#4095
 add w9,w9,#20
 lsr w10,w22,#12
 ldrh w10,[x27,x10,lsl #1]
 cmp w10,w9
 b.lo .Lut_orig
 add x10,x26,w22,uxtw
 ldr w9,[x10,#12]
 mov w11,#0x5b3d
 movk w11,#3,lsl 16
 cmp w9,w11
 b.ne .Lut_orig
 add x9,x26,w24,uxtw
 mov w11,#0x180
 movk w11,#0x95,lsl 16
 add x12,x26,w11,uxtw
 ldp q16,q17,[x12]
 ldp q18,q19,[x12,#32]
 ldr q20,[x9]
 fmul v16.4s,v16.4s,v20.s[0]
 fmul v17.4s,v17.4s,v20.s[1]
 fmul v18.4s,v18.4s,v20.s[2]
 fadd v16.4s,v19.4s,v16.4s
 fadd v16.4s,v17.4s,v16.4s
 fadd v16.4s,v16.4s,v18.4s
 cmp w15,#2
 b.eq .Lut_shadow
 str w24,[x10,#8]
 str w21,[x10,#16]
 mov w19,w21
 mov w20,w11
 stur q17,[x2,#136]
 stur q16,[x2,#152]
 stur q18,[x2,#168]
 str q16,[x9]
 b .L1049
.Lut_shadow:
 adrp x13,ut_check
 add x13,x13,:lo12:ut_check
 stp q17,q16,[x13]
 str q18,[x13,#32]
 str w24,[x13,#48]
 mov w14,#1
 str w14,[x13,#52]
.Lut_orig:
"""
body=body.replace(k,k+code)
k='.L1049:\n'
body=body.replace(k,k+'''
 adrp x13,ut_arm
 ldr w13,[x13,:lo12:ut_arm]
 cmp w13,#2
 b.ne .Lut_done
 adrp x13,ut_check
 add x13,x13,:lo12:ut_check
 ldr w14,[x13,#52]
 cbz w14,.Lut_done
 str wzr,[x13,#52]
 ldr w14,[x13,#48]
 cmp w19,w14
 b.ne .Lut_bad
 cmp w21,w14
 b.ne .Lut_bad
 cmp w24,w14
 b.ne .Lut_bad
 mov w15,#0x180
 movk w15,#0x95,lsl 16
 cmp w20,w15
 b.ne .Lut_bad
 add x10,x26,w22,uxtw
 ldr w15,[x10,#8]
 cmp w15,w14
 b.ne .Lut_bad
 ldr w15,[x10,#16]
 cmp w15,w14
 b.ne .Lut_bad
 add x10,x26,w14,uxtw
 ldp q16,q17,[x13]
 ldr q18,[x13,#32]
 ldur q19,[x2,#136]
 ldur q20,[x2,#152]
 ldur q21,[x2,#168]
 ldr q22,[x10]
 eor v19.16b,v19.16b,v16.16b
 eor v20.16b,v20.16b,v17.16b
 eor v21.16b,v21.16b,v18.16b
 eor v22.16b,v22.16b,v17.16b
 orr v19.16b,v19.16b,v20.16b
 orr v21.16b,v21.16b,v22.16b
 orr v19.16b,v19.16b,v21.16b
 umaxv b19,v19.16b
 umov w15,v19.b[0]
 cbnz w15,.Lut_bad
 ldr w15,[x13,#56]
 add w15,w15,#1
 str w15,[x13,#56]
 b .Lut_done
.Lut_bad:
 brk #1
.Lut_done:
''')
# Only the independent reference needs the check on return.
if '--verify' not in sys.argv:body=body[:body.index(k)+len(k)]+body[body.index('.Lut_done:\n')+len('.Lut_done:\n'):]
s=s[:a]+body+s[b:];asm=p.out/'update-transform.s';asm.write_text(s);o=asm.with_suffix('.o');subprocess.run(['cc','-c',asm,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0028.c.o'))]=str(o)
driver=r'''
unsigned ut_arm;_Alignas(16) unsigned ut_check[16];
void ut_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,ut_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)fprintf(stderr,"[UT_CHECK] %u\n",ut_check[14]);
 ut_arm=f<120?(getenv("NGB_OPEN_CHECK")?2:((((f/2+12345)*2654435761u>>31)^(f&1))^(getenv("NGB_OPEN_REVERSE")!=NULL))):0;
 last=now;prev=draws;
}
'''
if '--verify' not in sys.argv:
 driver=driver.replace('getenv("NGB_OPEN_CHECK")?2:', '')
p.driver(driver)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void ut_frame(unsigned,unsigned);ut_frame({arg},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
