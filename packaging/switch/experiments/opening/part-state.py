"""Group draws by 3078B0's live zero-based loop counter, compare effective state after sync."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;sys.path.insert(0,str(h.parents[1]/'perf'))
from native_probe import *
writers='--writers' in sys.argv
p=NativeProbe('opening-part-writers' if writers else 'opening-part-state');p.driver('')
s=(RUNTIME/'direct/hooks.c').read_text()
k='void ngb_direct_mesh_scope(int enter)\n{';assert s.count(k)==1
s=s.replace(k,r'''
unsigned part_no,part_on,part_frame,part_seq,part_calls,part_broken;
void part_flip(unsigned f){
 extern void part_report(unsigned);if(f==30||f==120)part_report(f);
 if(!f||f==30){part_calls=part_broken=0;}
 part_frame=f<120?f+1:0;part_on=0;
}
'''+k+r'''
 static unsigned last,sp0,lastframe;
 part_on=enter && part_frame && MEM32(esp)==0x003079cc;
 if(part_on){
   part_no=esi;
   if(!esi){++part_seq;++part_calls;}
   else if(esi!=last+1 || esp!=sp0 || lastframe!=part_frame){++part_broken;++part_seq;}
   sp0=esp;last=esi;lastframe=part_frame;
 }
''')
if writers:
 s=s.replace('int d3d_hook(int fn)\n{','unsigned part_setter[3];\nint d3d_hook(int fn)\n{\n if(fn==D3DF_D3DDevice_SetVertexShaderConstant1)++part_setter[0];if(fn==D3DF_D3DDevice_SetVertexShaderConstant4)++part_setter[1];if(fn==D3DF_D3DDevice_SetTransform)++part_setter[2];')
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(ROOT/'src/d3d/hle.cpp').read_text()
s='extern "C"{extern unsigned part_on,part_no,part_frame,part_seq,part_calls,part_broken;}\n'+s
k='void Draw(uint32_t prim, uint32_t start, uint32_t count, const uint8_t* indices) {'
s=s.replace(k,r'''
struct PartState {
 decltype(g_state.rs) rs;decltype(g_state.tss) tss;decltype(g_state.textures) textures;
 decltype(g_state.streams) streams;decltype(g_state.vsc) vsc;decltype(g_state.material) mat;
 uint32_t fixed[160];uint32_t simple[0x800];std::shared_ptr<gpu::VertexShader> vs;
};
static PartState last_part;
static unsigned counts[13],last_seq,last_no,last_frame;
static void observe_part(){
 if(!part_on){last_frame=0;return;}
 ++counts[0];
 bool cmp=part_seq==last_seq && last_frame==part_frame && part_no==last_no+1;
 auto &o=last_part;unsigned mask=0;
 auto field=[&](unsigned k,void *dst,const void *src,size_t bytes){if(cmp&&!std::memcmp(dst,src,bytes))mask|=1u<<k;std::memcpy(dst,src,bytes);};
 field(0,&o.rs,&g_state.rs,sizeof o.rs);field(1,&o.tss,&g_state.tss,sizeof o.tss);
 field(2,&o.textures,&g_state.textures,sizeof o.textures);field(3,&o.streams,&g_state.streams,sizeof o.streams);
 field(4,&o.vsc,&g_state.vsc,sizeof o.vsc);field(5,&o.mat,&g_state.material,sizeof o.mat);
 unsigned off=0;bool same=true;
 for(unsigned t=0;t<10;t++){auto idx=t<2?t+2:t<6?t+14:t+250;auto v=g_state.transforms[idx].data();if(cmp && std::memcmp(o.fixed+off,v,64))same=false;std::memcpy(o.fixed+off,v,64);off+=16;}
 if(same)mask|=64;
 field(7,o.simple,g_state.simple.data(),sizeof o.simple);
 if(o.vs==g_state.vs)mask|=256;o.vs=g_state.vs;
 if(cmp){++counts[1];for(unsigned i=0;i<9;i++)counts[i+2]+=(mask>>i)&1;counts[11]+=mask==511;}
 last_frame=part_frame;last_no=part_no;last_seq=part_seq;
}
extern "C" void part_report(unsigned f){
 fprintf(stderr,"[PARTS] %u parents=%u broken=%u",f,part_calls,part_broken);
 for(unsigned i=0;i<12;i++)fprintf(stderr," %u",counts[i]);fprintf(stderr,"\n");
 memset(counts,0,sizeof counts);
}
'''+k)
k='    SyncDeferred();';assert s.count(k)==1;s=s.replace(k,k+'observe_part();')
if writers:
 s='#include <stdint.h>\nextern "C"{extern unsigned part_setter[3];extern uint64_t ngb_material_hits[];}\n'+s
 k=' auto &o=last_part;';assert s.count(k)==1
 s=s.replace('static PartState last_part;', 'static PartState last_part;static uint64_t last_wr[5],wr[5],wr_pairs[5],any_vsc,any_mat;')
 s=s.replace(k,''' uint64_t cur[5]={ngb_material_hits[1],ngb_material_hits[2],part_setter[0],part_setter[1],part_setter[2]};
 bool v=false;for(unsigned i=0;i<5;i++){if(cmp && cur[i]!=last_wr[i]){wr[i]+=cur[i]-last_wr[i];wr_pairs[i]++;if(i<4)v=true;else any_mat++;}last_wr[i]=cur[i];}any_vsc+=v;
'''+k)
 k=' memset(counts,0,sizeof counts);';s=s.replace(k,''' fprintf(stderr,"[WRITERS] %u pairs=%u vsc_pairs=%llu transform_pairs=%llu",f,counts[1],(unsigned long long)any_vsc,(unsigned long long)any_mat);
 for(unsigned i=0;i<5;i++){fprintf(stderr," %llu:%llu",(unsigned long long)wr_pairs[i],(unsigned long long)wr[i]);wr_pairs[i]=wr[i]=0;}fputc(10,stderr);any_vsc=any_mat=0;
'''+k)
p.add('hle.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 assert s.count(k)==1;s=s.replace(k,k+f' extern void part_flip(unsigned);part_flip({f});')
p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
