"""Exact reuse of vertex programs selected during original opening frames 1..120."""
from pathlib import Path
import sys,subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
p=NativeProbe('opening-setup')
s=(ROOT/'src/d3d/hle.cpp').read_text()
def edit(old,new):
 global s
 assert s.count(old)==1,old
 s=s.replace(old,new)
edit('uint32_t g_program[136][4];','''extern "C" unsigned vs_arm;
struct Choice {unsigned h=0,at=0;std::shared_ptr<gpu::VertexShader> decl,vs;};
static Choice choices[64][4];
static unsigned rotor[64], attempts,hits,checked;
uint32_t g_program[136][4];''')
k='        auto vs = std::make_shared<gpu::VertexShader>();\n        auto it = g_vs.find(h);'
edit(k,'''        auto it=g_vs.find(h);
        Choice *slot=nullptr;
        bool hit=false;
        if(vs_arm){
            ++attempts;
            unsigned n=((h>>2)^at^(h>>11))&63;
            auto &set=choices[n];
            for(auto &entry:set){
                if(!entry.vs){if(!slot)slot=&entry;continue;}
                if(entry.h!=h || entry.at!=at || entry.decl.get()!=(it==g_vs.end()?nullptr:it->second.get()))continue;
                const auto &code=entry.vs->program;
                if(at>=136 ? code.empty() : !code.empty() && code.size()<=(136-at)*4 &&
                     !std::memcmp(code.data(),g_program[at],code.size()*4)){
                    slot=&entry;hit=true;break;
                }
            }
            if(hit){
                ++hits;
                if(vs_arm==1){g_selected=slot->vs;g_state.vs_handle=h|1;g_state.vs=g_selected;break;}
            }
            if(!slot)slot=&set[rotor[n]++&3];
        }
        auto vs=std::make_shared<gpu::VertexShader>();''')
edit('        g_selected = vs;', '''        if(hit){
            auto &v=*slot->vs;
            if(v.handle!=vs->handle||v.decl!=vs->decl||v.program!=vs->program||v.program_type!=vs->program_type||
               v.stream_stride!=vs->stream_stride||v.constants!=vs->constants)std::abort();
            for(unsigned i=0;i<v.inputs.size();i++){
                auto a=v.inputs[i],b=vs->inputs[i];if(a.stream!=b.stream||a.offset!=b.offset||a.type!=b.type)std::abort();
            }
            ++checked;
        }
        if(slot&&!hit)*slot={h,at,it==g_vs.end()?nullptr:it->second,vs};
        g_selected = vs;''')
edit('    g_selected.reset();','    for(auto &set:choices)for(auto &slot:set)slot={};\n    g_selected.reset();')
s+='\nextern "C" void vs_report(){std::fprintf(stderr,"[VS_CACHE] %u %u %u\\n",attempts,hits,checked);}\n'
p.add('hle.cpp',s)
vp='--viewport' in sys.argv
if vp:
 asm=(REGS/'recomp_0044.c.gated.s').read_text()
 a=asm.index('ngb_reg_d3d_orig_003C5FD0:');b=asm.index('\t.size\tngb_reg_d3d_orig_003C5FD0',a)
 body=asm[a:b];k='\tbl ngb_reg_checkpoint';assert body.count(k)==1
 body=body.replace(k,k+'''
 adrp x0,vs_arm
 ldr w0,[x0,:lo12:vs_arm]
 cbz w0,.Lvp_orig
 mov x0,x26
 mov w1,w22
 mov w2,w20
 mov w3,w21
 mov w4,w24
 mov w5,w25
 bl vp_before
 cbz w0,.Lvp_orig
 adrp x0,vp_ax
 ldr w19,[x0,:lo12:vp_ax]
 adrp x0,vp_dx
 ldr w21,[x0,:lo12:vp_dx]
 add w22,w22,#4
 b .Lvp_done
.Lvp_orig:''')
 k='\tldp\tx29, x30, [sp], 80';assert body.count(k)==1
 body=body.replace(k,''' adrp x0,vs_arm
 ldr w0,[x0,:lo12:vs_arm]
 cbz w0,.Lvp_done_original
 mov w0,w19
 mov w1,w21
 mov w2,w20
 mov w3,w22
 mov w4,w24
 mov w5,w25
 bl vp_after
 b .Lvp_done_original
.Lvp_done:
 ldp d14,d15,[sp,#16]
.Lvp_done_original:
'''+k)
 f=p.out/'vp.s';f.write_text(asm[:a]+body+asm[b:]);o=f.with_suffix('.o')
 subprocess.run(['cc','-c',f,'-o',o],check=True);p.link[p.link.index(str(REGS/'recomp_0044.c.o'))]=str(o)
driver=r'''
unsigned vs_arm;
extern void vs_report(void);
void vs_frame(unsigned f,unsigned draws){
 static uint64_t last; static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);
 uint64_t now=t.tv_sec*1000000000ull+t.tv_nsec;
 if(f&&last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\n",f,vs_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)vs_report();
 vs_arm=f>=120?0:getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 last=now;prev=draws;
}
'''
if vp:
 driver=driver.replace('extern void vs_report',Path(__file__).with_name('viewport.inc').read_text()+'\nextern void vs_report')
 driver=driver.replace('if(f==120)vs_report();','if(f==120){vs_report();fprintf(stderr,"[VIEWPORT] %u %u %u\\n",vp_calls,vp_hits,vp_checked);}')
p.driver(driver)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 edit(k,k+f' extern void vs_frame(unsigned,unsigned);vs_frame({arg},draws);')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
