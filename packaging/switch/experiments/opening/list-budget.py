"""Time entire model-list callbacks, including tail calls, without nested double counts."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
src=(REGS/'recomp_0016.c.gated.s').read_text()
# These private ABI callbacks take guest state in x19..x28.  Save all
# volatile GPRs and SIMD registers around the C clock hook, plus NZCV.
def event(i):
 save=['sub sp,sp,#688','stp x18,x30,[sp,#144]','mrs x18,nzcv','str x18,[sp,#160]']
 load=['ldr x18,[sp,#160]','msr nzcv,x18','ldp x18,x30,[sp,#144]','add sp,sp,#688']
 for j in range(0,18,2):
  save += [f'stp x{j},x{j+1},[sp,#{8*j}]']
  load.insert(0,f'ldp x{j},x{j+1},[sp,#{8*j}]')
 for j in range(0,32,2):
  save += [f'stp q{j},q{j+1},[sp,#{176+16*j}]']
  load.insert(0,f'ldp q{j},q{j+1},[sp,#{176+16*j}]')
 return '\n'.join(save+[f'mov w0,#{i}','bl list_clock']+load)
for i,name in enumerate(('001CB3B0','001CB510','001CB9A0'),1):
 k='ngb_reg_sub_'+name+':\n';assert src.count(k)==1
 src=src.replace(k,k+event(i)+f'\nstp x29,x30,[sp,#-16]!\nbl .Llist_{i}\nldp x29,x30,[sp],#16\n'+event(i+8)+f'\nret\n.Llist_{i}:\n')
f=p.out/'list-budget.s';f.write_text(src);o=f.with_suffix('.o')
subprocess.run(['cc','-c',f,'-o',o],check=True)
p.link[p.link.index(str(REGS/'recomp_0016.c.o'))]=str(o)
p.driver(r'''
static _Thread_local unsigned lb_f,lb_depth,lb_stack[32],lb_n[4];
static _Thread_local uint64_t lb_last,lb_sum[4];
static void lb_charge(void){
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=(uint64_t)t.tv_sec*1000000000+t.tv_nsec;
 if(lb_f)lb_sum[lb_stack[lb_depth]]+=now-lb_last;
 lb_last=now;
}
void list_clock(unsigned i){
 if(lb_f)lb_charge();
 if(i<8){if(lb_depth==31)abort();lb_stack[++lb_depth]=i;if(lb_f)++lb_n[i];}
 else{if(!lb_depth||lb_stack[lb_depth]!=(i-8))abort();--lb_depth;}
}
void list_flip(unsigned f){
 lb_charge();
 if(f){if(f!=lb_f)abort();fprintf(stderr,"[LIST_BUDGET] %u",f);
 for(unsigned i=0;i<4;i++)fprintf(stderr," %u:%llu",lb_n[i],(unsigned long long)lb_sum[i]);
 fprintf(stderr,"\n");}
 memset(lb_sum,0,sizeof lb_sum);memset(lb_n,0,sizeof lb_n);lb_f=f<120?f+1:0;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void list_flip(unsigned);list_flip({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
