"""Inclusive host elapsed ticks by actual node kind, prefix vs full call."""
import re,subprocess
def install(p,regs,src):
 name='recomp_0016.c';s=(regs/(name+'.gated.s')).read_text()
 a=s.index('ngb_reg_sub_001CBED0:\n');z=s.index('\t.size\tngb_reg_sub_001CBED0',a);b=s[a:z]
 assert not re.search(r'\b[wx](?:16|17)\b',b)
 def rep(k,v):
  nonlocal b
  assert b.count(k)==1,k
  b=b.replace(k,v)
 # Keep original SP-relative locals in place; use a private slot on each
 # native frame, including across guest callbacks, recursion or fiber yields.
 rep('[sp, -96]!','[sp, -128]!');rep('cfa_offset 96','cfa_offset 128');rep('29, -96','29, -128');rep('30, -88','30, -120')
 k='\t.cfi_startproc\n';rep(k,k+' isb\n mrs x16,cntvct_el0\n')
 k='\t.cfi_offset 30, -120\n';rep(k,k+' str x16,[sp,#96]\n adrp x16,kind_frame\n ldr w16,[x16,:lo12:kind_frame]\n str w16,[sp,#120]\n')
 k='.L40789:\n\tldr\tw0, [x0]\n';rep(k,k+''' isb
 mrs x16,cntvct_el0
 str x16,[sp,#104]
 mov w16,#16
 cmp w0,w16
 csel w16,w0,w16,lo
 str w16,[sp,#112]
''')
 k='\tldp\tx29, x30, [sp], 96';rep(k,''' isb
 mrs x16,cntvct_el0
 ldr w17,[sp,#120]
 cbz w17,97f
 adrp x1,kind_frame
 ldr w1,[x1,:lo12:kind_frame]
 cmp w1,w17
 b.ne 97f
 ldr w17,[sp,#112]
 adrp x1,kind_time
 add x1,x1,:lo12:kind_time
 add x1,x1,x17,lsl #5
 ldp x2,x3,[sp,#96]
 sub x3,x3,x2
 sub x16,x16,x2
 ldp x2,x17,[x1]
 add x2,x2,#1
 add x17,x17,x3
 stp x2,x17,[x1]
 ldr x2,[x1,#16]
 add x2,x2,x16
 str x2,[x1,#16]
97: ldp x29,x30,[sp],128''')
 f=p.out/'time.s';obj=f.with_suffix('.o');f.write_text(s[:a]+b+s[z:]);subprocess.run(['cc','-c',f,'-o',obj],check=True);f.unlink();p.link[p.link.index(str(regs/(name+'.o')))]=str(obj)
 return src.replace('void __real_ngb_kernel_log',r'''
uint64_t kind_time[17][4];unsigned kind_frame;
void phase_flip(unsigned f){uint64_t hz;__asm__("mrs %0,cntfrq_el0":"=r"(hz));
 if(f==30||f==120){for(unsigned i=0;i<17;i++)if(kind_time[i][0])fprintf(stderr,"[ACTOR_TIME] %u %u %llu %llu %llu %llu\n",f,i,(unsigned long long)hz,(unsigned long long)kind_time[i][0],(unsigned long long)kind_time[i][1],(unsigned long long)kind_time[i][2]);}
 if(!f||f==30){memset(kind_time,0,sizeof kind_time);}kind_frame=f<120?f+1:0;}
void __real_ngb_kernel_log''',1)
