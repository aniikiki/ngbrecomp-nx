"""Specialize the 4x4 matrix transpose in the model setup callback; retain
the original body for partial physical overlap and non-normal floats."""
from pathlib import Path
import sys,subprocess as sp,shlex
here=Path(__file__).resolve().parent;perf=here.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
d=BASE/'core-perf/transpose';d.mkdir(exist_ok=True)
if sys.argv[1]=='cross':
 n='recomp_0039.c';s=(BASE/'gen'/n).read_text()
 tag='    RECOMP_ENTRY(0x0037A480u);';assert s.count(tag)==1
 s='extern unsigned trial_variant,transpose_hits;\n'+s.replace(tag,tag+'''
    if(trial_variant){
        uint32_t output=MEM32(esp+4), input=MEM32(esp+8);
        const uint32_t *source=ngb_ram_span(input,64); uint32_t *dest=ngb_ram_span(output,64);
        uintptr_t a=(uintptr_t)source,b=(uintptr_t)dest;
        if(source && dest && !((a|b)&3) && (a==b || a+64<=b || b+64<=a)){
            uint32x4x4_t v=vld4q_u32(source);
            // x87 loads convert six lower/upper entries via double. Avoid
            // platform-specific behavior for NaNs and subnormal inputs.
            uint32x4_t bad=vdupq_n_u32(0);
            for(unsigned i=0;i<4;i++){
                uint32x4_t mag=vandq_u32(v.val[i],vdupq_n_u32(0x7fffffffu));
                bad=vorrq_u32(bad,vorrq_u32(vcgeq_u32(mag,vdupq_n_u32(0x7f800000)),
                    vandq_u32(vcltq_u32(mag,vdupq_n_u32(0x00800000)),vcgtq_u32(mag,vdupq_n_u32(0)))));
            }
            if(!vmaxvq_u32(bad)){
                g_fp_stack[(g_fp_top+6)&7]=(double)vgetq_lane_f32(vreinterpretq_f32_u32(v.val[0]),1);
                g_fp_stack[(g_fp_top+7)&7]=(double)vgetq_lane_f32(vreinterpretq_f32_u32(v.val[3]),2);
                eax=output;
                edx=input==output?vgetq_lane_u32(v.val[2],3):vgetq_lane_u32(v.val[2],2);
                ecx=input==output?input:vgetq_lane_u32(v.val[3],3);
                vst1q_u32_x4(dest,v);esp+=12;++transpose_hits;return;
            }
        }
    }''')
 f=d/n;f.write_text(s)
 c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=BASE/'switch',text=True).splitlines() if x.endswith('/'+n))
 c[c.index('-o')+1]=str(f)+'.o';c[c.index('-MF')+1]=str(f)+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=BASE/'switch',check=True)
else:
 p=NativeProbe('transpose');p.driver('unsigned transpose_hits;\n'+(perf/'trial.inc').read_text())
 p.link[next(i for i,v in enumerate(p.link) if v.endswith('/recomp_0039.o'))]=str(d/'recomp_0039.c.o')
 s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
 p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned transpose_hits;if(!(scene_flips%120))fprintf(stderr,"[TRANSPOSE] %u %u\\n",scene_flips,transpose_hits);ngb_trial_flip(scene_flips,draws);'));p.link.insert(1,'-Wl,--strip-debug');p.finish()
