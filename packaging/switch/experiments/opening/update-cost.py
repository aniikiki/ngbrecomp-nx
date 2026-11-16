"""Charge 38C70 -> 35A00 and selected nested calls exclusive of instrumented children."""
from pathlib import Path
import re,sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
records=[]
candidates='--candidates' in sys.argv
for unit,parents in [(1,['00038C70','00035A00','00035B90']),(9,['0013C050','0013C110']+(['0013D330'] if candidates else []))]:
 f=REGS/f'recomp_{unit:04d}.c.gated.s';s=f.read_text();wr=''
 for parent in parents:
  a=s.index(f'ngb_reg_sub_{parent}:');b=s.index(f'\t.size\tngb_reg_sub_{parent}',a);body=s[a:b]
  targets=sorted(set(re.findall(r'\bbl\s+(ngb_(?:gate|reg)_sub_\w+)',body)))
  if parent=='00038C70':targets=['ngb_reg_sub_00035A00']
  for target in targets:
   idx=len(records)+1;records.append((parent,target));label=f'uc_edge_{idx}'
   if candidates and parent=='0013D330' and target=='ngb_reg_sub_00140AF0':
    for site in range(2):
     key='bl\t'+target
     pos=body.index(key)
     code=f'\n adrp x16,uc_depth\n ldr w17,[x16,:lo12:uc_depth]\n cbz w17,1f\n adrp x16,uc_result\n add x16,x16,:lo12:uc_result\n add x16,x16,#{site*8}\n cbz w19,2f\n add x16,x16,#4\n2: ldr w17,[x16]\n add w17,w17,#1\n str w17,[x16]\n1:\n'
     body=body[:pos]+f'bl {label}'+code+body[pos+len(key):]
    n=2
   else:body,n=re.subn(r'(\bbl\s+)'+target+r'\b',lambda m:m[1]+label,body);assert n
   def tick(event):
    v=['sub sp,sp,#688','stp x18,x30,[sp,#144]','mrs x18,nzcv','str x18,[sp,#160]']
    for j in range(0,18,2):v.append(f'stp x{j},x{j+1},[sp,#{8*j}]')
    for j in range(0,32,2):v.append(f'stp q{j},q{j+1},[sp,#{176+16*j}]')
    v+= [f'mov w0,#{event}','bl uc_tick']
    for j in range(0,32,2):v.append(f'ldp q{j},q{j+1},[sp,#{176+16*j}]')
    for j in range(0,18,2):v.append(f'ldp x{j},x{j+1},[sp,#{8*j}]')
    return '\n'.join(v+['ldr x18,[sp,#160]','msr nzcv,x18','ldp x18,x30,[sp,#144]','add sp,sp,#688'])
   wr+=f'{label}:\n'+tick(idx)+f'\nstp x29,x30,[sp,#-16]!\n bl {target}\n ldp x29,x30,[sp],#16\n'+tick(128+idx)+'\nret\n'
  s=s[:a]+body+s[b:]
 out=p.out/f'uc-{unit}.s';out.write_text(s+'\n.text\n'+wr)
 obj=out.with_suffix('.o');subprocess.run(['cc','-c',out,'-o',obj],check=True);p.link[p.link.index(str(REGS/f'recomp_{unit:04d}.c.o'))]=str(obj)
assert len(records)<64
p.driver(r'''
unsigned uc_depth,uc_result[4];static unsigned uc_active,uc_stack[128],uc_count[64];static uint64_t uc_last,uc_sum[64];
void uc_tick(unsigned ev){
 if(!uc_active)return;
 unsigned k=ev&127;
 if(!uc_depth && ev!=1)return;
 struct timespec ts;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts);
 uint64_t now=ts.tv_sec*1000000000ull+ts.tv_nsec;
 if(uc_depth)uc_sum[uc_stack[uc_depth-1]]+=now-uc_last;
 uc_last=now;
 if(ev&128){if(uc_stack[--uc_depth]!=k)abort();}
 else{if(uc_depth==128)abort();uc_stack[uc_depth++]=k;++uc_count[k];}
}
void uc_frame(unsigned f){if(f==120){if(uc_depth)abort();fprintf(stderr,"[CANDIDATES] %u %u %u %u\n",uc_result[0],uc_result[1],uc_result[2],uc_result[3]);for(unsigned k=1;k<64;k++)if(uc_count[k])fprintf(stderr,"[UC] %u %u %llu\n",k,uc_count[k],(unsigned long long)uc_sum[k]);}uc_active=f<120;}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void uc_frame(unsigned);uc_frame({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
(p.out/('candidate-edges.txt' if candidates else 'update-edges.txt')).write_text('\n'.join(f'{i} {a} {b}' for i,(a,b) in enumerate(records,1)))
