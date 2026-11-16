"""Instrument the original setup's return PCs for scene flips 1..120.
Use live effective state for equality, rather than matching the previous model's arguments."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
p=NativeProbe('opening-setup');p.driver('')
s=(ROOT/'src/d3d/hle.cpp').read_text()
s+='''
extern "C" { unsigned opening_frame; }
struct OpeningCount {unsigned total,equal;};
static OpeningCount counts[0x300];
extern "C" void opening_observe(unsigned fn,unsigned site,unsigned a,unsigned c,unsigned d,unsigned b,unsigned sp){
 if(!opening_frame || site<0x1d6e20 || site>=0x1d7100)return;
 bool eq=false;unsigned n=0;
 switch(fn){
 case D3DF_D3DDevice_SetVertexShaderConstant1: n=1;break;
 case D3DF_D3DDevice_SetVertexShaderConstant4: n=4;break;
 case D3DF_D3DDevice_SetRenderState_Simple:eq=g_state.simple[(c&0x1ffc)/4]==d;break;
 case D3DF_D3DDevice_SetPixelShaderConstant:
   if(!a||a>16||c>16-a)return;
   eq=!std::memcmp(g_state.psc[c].data(),HostPtr(R32(sp+4)),16*a);break;
 case D3DF_D3DDevice_SelectVertexShader:{
   auto sh=g_state.vs; auto it=g_vs.find(a);
   if(sh && sh.get()==g_selected.get() && g_state.vs_handle==(a|1) && sh->handle==a &&
      (it==g_vs.end()?sh->decl.empty():sh->decl==it->second->decl)){
    unsigned len=0;
    if(b<136){do{++len;}while(len<136-b && !(g_program[b+len-1][3]&1));}
    eq=sh->program.size()==4*len && (!len || !std::memcmp(sh->program.data(),g_program[b],16*len));
   }break;}
 default:return;
 }
 if(n){if(c>192-n)return;eq=!std::memcmp(HostPtr(kVsConstants+16*c),HostPtr(d),16*n);}
 auto &row=counts[site-0x1d6e20];++row.total;row.equal+=eq;
}
extern "C" void opening_end(unsigned f){
 if(f==120){for(unsigned i=0;i<0x300;i++)if(counts[i].total)
 std::fprintf(stderr,"[OPEN_SETUP] pc=%08x calls=%u same=%u\\n",0x1d6e20+i,counts[i].total,counts[i].equal);}
 opening_frame=f<120?f+1:0;
}
'''
p.add('hle.cpp',s)
s=(RUNTIME/'direct/hooks.c').read_text();k='int d3d_hook(int fn)\n{'
s=s.replace(k,k+'''\n    extern unsigned opening_frame;
    extern void opening_observe(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
    if(opening_frame)opening_observe(fn,MEM32(esp),eax,ecx,edx,ebx,esp);''')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(RUNTIME/'scene/bridge.c').read_text()
for k,call in [('            ngb_direct_reset_stats();','opening_end(0);'),('    ++scene_flips;','opening_end(scene_flips);')]:
 assert s.count(k)==1;s=s.replace(k,k+' extern void opening_end(unsigned);'+call)
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
