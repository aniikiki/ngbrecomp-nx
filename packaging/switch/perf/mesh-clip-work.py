"""Offline join: cost of whole producer mesh scopes vs later proven clipped draws.
The ID travels inside the recorded command; game and renderer progress independently."""
from pathlib import Path
import json
import shlex
import subprocess as sp
root=Path('/work')
core=root/'build/switch-runtime/core-perf'
host=core.parent/'host'
out=core/'mesh-clip'
out.mkdir(exist_ok=True)
cmds=sp.check_output(['ninja','-t','commands','ngb-runtime-test'],cwd=host,text=True).splitlines()
link=json.loads((core/'exact-link.json').read_text())
def obj(n,s,extra=()):
    c=next(shlex.split(x) for x in cmds if x.endswith('/'+n))
    orig=Path(c[-1]);f=out/orig.name;f.write_text(s);o=str(f)+'.o'
    c[c.index('-MF')+1]=o+'.d';c[c.index('-o')+1]=o;c[-1]=str(f)
    c[1:1]=['-I'+str(orig.parent),*extra];sp.run(c,cwd=host,check=True)
    return o
def rep(a,b):
    global s
    assert s.count(a)==1,a
    s=s.replace(a,b)
r=root/'packaging/switch/runtime'
s=(r/'direct/hooks.c').read_text()
tag='void ngb_direct_mesh_scope(int enter)\n{'
rep(tag,'''#include <time.h>
static unsigned mc_seq,mc_f,mc_n,mc_mesh;
static uint64_t mc_start;
unsigned mc_id,mc_commands;
static FILE *mc_file;
static uint64_t mc_clock(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
'''+tag+'''
    if(enter && !index_time.mesh_depth && mc_f>=1800 && mc_f<1920){
        if(!mc_file){mc_file=fopen("/work/build/switch-runtime/core-perf/mesh-cost.bin","wb");if(!mc_file)abort();}
        mc_id=++mc_seq;mc_n=mc_f+1;mc_mesh=MEM32(esp+4);mc_commands=0;mc_start=mc_clock();
    }
    if(!enter && index_time.mesh_depth==1 && mc_id){
        uint32_t row[]={mc_id,mc_n,mc_mesh,mc_commands,(uint32_t)(mc_clock()-mc_start)};
        if(fwrite(row,sizeof(row),1,mc_file)!=1)abort();
        if(mc_n==1920)fflush(mc_file);
        mc_id=0;
    }
''')
rep('    measured_frames += ngb_direct_detail_frame;','    extern void mc_frame(unsigned); mc_frame(completed);\n    measured_frames += ngb_direct_detail_frame;')
s+='\nvoid mc_frame(unsigned f){mc_f=f;}\n'
link[link.index(str(core/'exact-hooks.c.o'))]=obj('direct/hooks.c',s,['-include',str(r/'switch_guest_regs.h')])
s=(root/'src/d3d/gpu/threaded.cpp').read_text()
rep('struct Cmd {','extern "C" { extern unsigned mc_id,mc_commands; thread_local unsigned mc_render; }\nstruct Cmd {')
rep('    Surface s1, s2;', '    Surface s1, s2; unsigned mc=0;')
rep('if (prim == 6 && prev.a == prim','if (!mc_id && !prev.mc && prim == 6 && prev.a == prim')
rep('        Cmd c{Op::Draw};','        Cmd c{Op::Draw}; c.mc=mc_id; if(mc_id)++mc_commands;')
rep('            case Op::Draw:','            case Op::Draw: mc_render=c.mc;')
link.insert(1,obj('gpu/threaded.cpp',s))
s=(root/'src/d3d/vk/backend.cpp').read_text()
# Borrow the exact current pipeline WVP computation, before any cull decision.
matrix="        float vpm[16];RigidViewport(s,gw,gh,vpm);RigidMatrices(s,vpm,wv,m);"
helper=Path(__file__).with_name('rigid-planes.inc').read_text()
tag='void VulkanBackend::CapturePeek('
rep(tag,helper+'''
extern "C" {extern thread_local unsigned mc_render;}
struct MeshClass {
    unsigned id, outside=0;
    ~MeshClass(){ if(!id)return;static FILE *f=fopen("/work/build/switch-runtime/core-perf/mesh-draw.bin","wb");
        uint32_t row[]={id,outside};if(!f || fwrite(row,sizeof(row),1,f)!=1)std::abort();
        if(!(id%256))fflush(f); }
};
'''+tag)
rep('    st_.draws++;','    MeshClass observation{mc_render};\n    st_.draws++;')
tag='    rt_draws_[s.rt.data]++;'
rep(tag,tag+'''
    if(observation.id && !vis_on_ && !ContinuousGlowEnabled() && !s.rs[kRsVertexBlend] &&
       (s.vs_handle==0x142 || s.vs_handle==0x152 || s.vs_handle==0x112)){
        uint32_t gw,gh;SurfaceSize(rt?s.rt:s.zs,gw,gh);
        if(gw && gh){float wv[16],wvp[16],full[16],m[16];
'''+matrix+'''
        observation.outside=RigidBoundsPrediction(a,m)==2;}
    }
''')
link.insert(1,obj('vk/backend.cpp',s))
link[link.index('-o')+1]=str(out/'replay');sp.run(link,cwd=host,check=True)
