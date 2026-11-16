"""Observe three loop bodies in the release's private ARM implementation."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(REGS/'recomp_0001.c.gated.s').read_text()
i=s.index('ngb_reg_sub_00035A00:');j=s.index('\t.size\tngb_reg_sub_00035A00',i)
body=s[i:j]
for k,anchor in enumerate(['\tbl ngb_reg_checkpoint','\tbl\tngb_reg_sub_00035B90','.L20816:\n\tldrb\tw2, [x0]','\tbl\tngb_reg_sub_0003C7F0','\tbl\tngb_reg_sub_00305D60']):
    assert body.count(anchor)==1
    call=f'\n stp x16,x30,[sp,#-16]!\n mov w16,#{k}\n bl loop_probe\n ldp x16,x30,[sp],#16\n'
    body=body.replace(anchor,anchor+call if k in (0,2) else call+anchor)
s=s[:i]+body+s[j:]
wrapper=['.text','loop_probe:','sub sp,sp,#688','stp x16,x17,[sp,#128]','mrs x17,nzcv','stp x17,x30,[sp,#144]','str x18,[sp,#160]']
for k in range(0,16,2):wrapper.append(f'stp x{k},x{k+1},[sp,#{k*8}]')
for k in range(0,32,2):wrapper.append(f'stp q{k},q{k+1},[sp,#{176+16*k}]')
wrapper+=['mov w0,w16','mov w1,w19','mov w3,w24','mov x4,x26','mov w5,w25','bl loop_hit']
for k in range(0,32,2):wrapper.append(f'ldp q{k},q{k+1},[sp,#{176+16*k}]')
for k in range(0,16,2):wrapper.append(f'ldp x{k},x{k+1},[sp,#{k*8}]')
wrapper+=['ldr x18,[sp,#160]','ldp x17,x30,[sp,#144]','msr nzcv,x17','ldp x16,x17,[sp,#128]','add sp,sp,#688','ret']
f=p.out/'update-loops.s';f.write_text(s+'\n'+'\n'.join(wrapper)+'\n')
o=p.out/'update-loops.o';subprocess.run(['cc','-c',f,'-o',o],check=True)
p.link[p.link.index(str(REGS/'recomp_0001.c.o'))]=str(o)
p.driver(r'''
static unsigned loops_active,nloops[5],identical[5],prevvalid[5][64],overflows[5],unchanged_flags;
static unsigned char prevkeys[5][64][128];
void loop_hit(unsigned k,unsigned ax,unsigned type,unsigned si,unsigned char*mem,unsigned di){
 if(!loops_active)return;
 ++nloops[k];if(k<2)return;
 unsigned ix=k==2?ax:k==3?di:(si-0x494be0)/64;
 if(ix>=64){++overflows[k];return;}
 unsigned char key[128];unsigned len=0;
 if(k==2){key[0]=type;len=1;
  unchanged_flags+=(mem[0x4b22b0+ix]==(type!=3) && mem[0x496870+ix]==(type==3?0:7));}
 else if(k==3){if(ax!=0x494be0+64*ix || si!=0x495be0+16*ix)abort();
  for(unsigned v=0;v<3;v++){memcpy(key+12*v,mem+ax+16*v,12);}len=36;}
 else{if(si!=0x494be0+64*ix)abort();
  memcpy(key,mem+si,48);memcpy(key+48,mem+0x950180,64);len=112;}
 if(prevvalid[k][ix] && !memcmp(prevkeys[k][ix],key,len))++identical[k];
 memcpy(prevkeys[k][ix],key,len);prevvalid[k][ix]=1;
}
void loop_frame(unsigned f){
 if(f&&loops_active){fprintf(stderr,"[UPDATE_LOOPS] %u",f);for(unsigned k=0;k<5;k++)fprintf(stderr," %u:%u:%u",nloops[k],identical[k],overflows[k]);fprintf(stderr," %u\n",unchanged_flags);}
 memset(nloops,0,sizeof nloops);memset(identical,0,sizeof identical);memset(overflows,0,sizeof overflows);unchanged_flags=0;loops_active=f<120;
}
''')
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void loop_frame(unsigned);loop_frame({arg});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
