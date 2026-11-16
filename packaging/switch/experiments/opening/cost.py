"""Measure mutually exclusive time inside the actual 1D7100 -> 1D6E20 path.
ARM wrapper preserves x0..x18 and q0..q7 around the clock at both edges."""
from pathlib import Path
import re,subprocess,sys
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[1]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(REGS/'recomp_0016.c.gated.s').read_text()
key='\tbl\tngb_reg_sub_001D6E20';a=s.index('ngb_reg_sub_001D7100:');b=s.index('\t.size\tngb_reg_sub_001D7100',a);assert s.count(key,a,b)==1
s=s[:a]+s[a:b].replace(key,'\tbl openclock_root')+s[b:]
a=s.index('ngb_reg_sub_001D6E20:');b=s.index('\t.size\tngb_reg_sub_001D6E20',a)
targets=sorted(set(re.findall(r'\bbl (ngb_gate_sub_\w+)',s[a:b])))
part=s[a:b]
for t in targets:part=part.replace('bl '+t,'bl openclock_'+t)
s=s[:a]+part+s[b:]
for k,t in enumerate(['ngb_reg_sub_001D6E20',*targets]):
 lab='openclock_'+(t if k else 'root')
 def measure(event):
  out=['sub sp,sp,#288']
  for i in range(0,18,2):out+=[f'stp x{i},x{i+1},[sp,#{i*8}]']
  out+=['stp x18,x30,[sp,#144]']
  for i in range(0,8,2):out+=[f'stp q{i},q{i+1},[sp,#{160+i*16}]']
  out += [f'mov w0,#{event}','bl opening_cost_event']
  for i in range(0,8,2):out+=[f'ldp q{i},q{i+1},[sp,#{160+i*16}]']
  for i in range(0,18,2):out+=[f'ldp x{i},x{i+1},[sp,#{i*8}]']
  return '\n'.join(out+['ldp x18,x30,[sp,#144]','add sp,sp,#288'])
 s+=f'\n.text\n.p2align 2\n{lab}:\n'+measure(k+1)+f'\nstp x29,x30,[sp,#-16]!\n bl {t}\n ldp x29,x30,[sp],#16\n'+measure(128+k+1)+'\nret\n'
f=p.out/'setup-clock.s';f.write_text(s);o=p.out/'setup-clock.o';subprocess.run(['cc','-c',f,'-o',o],check=True)
p.link[p.link.index(str(REGS/'recomp_0016.c.o'))]=str(o)
p.driver('''
static uint64_t opening_t,opening_sum[64];static unsigned opening_n[64],opening_depth,opening_keys[64],opening_frame;
void opening_cost_event(unsigned event){
 if(!opening_frame)return;
 unsigned exiting=event>=128,key=event&127;
 if(!opening_depth && (key!=1 || exiting))return;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=(uint64_t)t.tv_sec*1000000000+t.tv_nsec;
 if(opening_depth)opening_sum[opening_keys[opening_depth-1]]+=now-opening_t;
 opening_t=now;
 if(exiting){if(opening_keys[--opening_depth]!=key)abort();}
 else{if(opening_depth==63)abort();opening_keys[opening_depth++]=key;++opening_n[key];}
}
void opening_cost_flip(unsigned f){
 if(f==120){for(unsigned i=1;i<64;i++)if(opening_n[i])fprintf(stderr,"[SETUP_COST] %u %u %llu\\n",i,opening_n[i],(unsigned long long)opening_sum[i]);}
 opening_frame=f<120?f+1:0;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 s=s.replace(k,k+f' extern void opening_cost_flip(unsigned);opening_cost_flip({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');(p.out/'cost-keys.txt').write_text('\n'.join(['enclosing routine',*targets]));p.finish()
