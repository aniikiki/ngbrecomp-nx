"""Opening producer costs and inputs joined to the actual render-thread cull; never skip a draw."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'perf'))
from native_probe import *
early='--early' in sys.argv
bindings='--siblings' in sys.argv
parents=bindings or '--parents' in sys.argv
p=NativeProbe('opening-clip-siblings' if bindings else 'opening-clip-parents' if parents else 'opening-clip-early' if early else 'opening-clip-join');out=str(p.out)+'/'
def rep(s,a,b):assert s.count(a)==1,a;return s.replace(a,b)
s=(RUNTIME/'direct/hooks.c').read_text()
k='void ngb_direct_mesh_scope(int enter)\n{'
s=rep(s,k,r'''
#include <time.h>
static unsigned jf,jseq,jkey,jpc;
unsigned jid,jcmd;static unsigned jmat[48];static uint64_t jt;
static uint64_t jnow(void){struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
void jflip(unsigned f){if(jid)abort();jf=f<120?f+1:0;}
'''+k+r'''
 if(enter&&jf){if(jid||index_time.mesh_depth)abort();jid=++jseq;jcmd=0;jkey=MEM32(esp+4);jpc=MEM32(esp);
 unsigned dev=MEM32(0x3d83c8);if(!dev)abort();
 for(unsigned i=0;i<3;i++)memcpy(jmat+16*i,(const void*)ngb_guest_pointer(dev+0xc60+64*(i==0?6:i-1),64),64);
 jt=jnow();}
 if(!enter&&jid){unsigned ns=(unsigned)(jnow()-jt);
 static FILE *fp;if(!fp)fp=fopen("OUTproducer.bin","wb");
 unsigned row[]={jid,jf,jkey,jpc,jcmd,ns};if(fwrite(row,sizeof row,1,fp)!=1||fwrite(jmat,sizeof jmat,1,fp)!=1)abort();jid=0;}
'''.replace('OUT',out))
if parents:
 # 3078B0 preserves the loop index in ESI. Four pushes from 3079BA
 # to the callee put the parent's base argument at [esp+0x34].
 a=s.index(' unsigned dev=MEM32(0x3d83c8);',s.index('if(enter&&jf)'))
 b=s.index(' jt=jnow();',a)
 s=s[:a]+""" if(jpc==0x3079cc){unsigned base=MEM32(esp+0x34);
 jmat[0]=esi;jmat[1]=MEM32(base+8);jmat[2]=base;
 if(esi>=jmat[1] || MEM32(base+0x94+32*esi)!=jkey)abort();}
 else jmat[0]=jmat[1]=jmat[2]=0;
 """+s[b:]
 s=rep(s,'fwrite(jmat,sizeof jmat,1,fp)','fwrite(jmat,12,1,fp)')
if early:
 s=rep(s,'jt=jnow();','extern void jearly(unsigned,const unsigned*);jearly(jid,jmat);jt=jnow();')
 b=(ROOT/'src/d3d/vk/backend.cpp').read_text()
 math=b[b.index('void MatMul('):b.index('#include "spark_aspect.h"')]+b[b.index('static void RigidViewport'):b.index('#ifdef NGB_RIGID_CLIP',b.index('static void RigidViewport'))]
 k2='gpu::State g_state;';h=(ROOT/'src/d3d/hle.cpp').read_text()
 add=math.replace('const State&','const gpu::State&')+r'''
extern "C" void jearly(unsigned id,const unsigned* mat){
 float v[16],wv[16],wvp[16],full[16],clip[16],m[48];memcpy(m,mat,sizeof m);
 uint32_t w,h;gpu::SurfaceSize(g_state.rt,w,h);if(!w||!h)memset(clip,0,sizeof clip);
 else {RigidViewport(g_state,w,h,v);MatMul(m,m+16,wv);MatMul(wv,m+32,wvp);MatMul(wvp,v,full);Transpose(full,clip);}
 static FILE*fp=fopen("OUTentry.bin","wb");if(fwrite(&id,4,1,fp)!=1||fwrite(clip,64,1,fp)!=1)abort();
}
'''.replace('OUT',out)
 p.add('hle.cpp',rep(h,k2,k2+'\n'+add))
p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',s,['-include',str(RUNTIME/'switch_guest_regs.h')])
s=(ROOT/'src/d3d/gpu/threaded.cpp').read_text()
s=rep(s,'struct Cmd {','extern "C"{extern unsigned jid,jcmd;thread_local unsigned jrender;}\nstruct Cmd {')
s=rep(s,'    Surface s1, s2;','    Surface s1, s2; unsigned join_id=0;')
s=rep(s,'        Cmd c{Op::Draw};','        Cmd c{Op::Draw}; c.join_id=jid;if(jid)++jcmd;')
s=rep(s,'                ++merged_strips_;','                if(jid||prev.join_id)std::abort();++merged_strips_;')
s=rep(s,'            case Op::Draw:','            case Op::Draw: jrender=c.join_id;')
p.add('gpu/threaded.cpp',s)
s=(ROOT/'src/d3d/vk/backend.cpp').read_text()
k='void VulkanBackend::CapturePeek('
s=rep(s,k,r'''
extern "C" {extern thread_local unsigned jrender;}
struct JoinDraw{unsigned id,stage=0;float mats[48]{},clip[16]{},box[6]{};
 ~JoinDraw(){if(!id)return;static FILE *fp=fopen("OUTdraw.bin","wb");
 if(fwrite(this,sizeof(*this),1,fp)!=1)std::abort();}
 void bounds(const gpu::Assembled& a){
 auto e=a.elements[0];if(!(a.regs&1)||(e.format!=6&&e.format!=2)||e.buffer>=a.buffer_count)return;
 auto &b=a.buffers[e.buffer];if(!b.src||b.stride<12||e.offset+12u>b.stride||e.offset+12u>b.bytes)return;
 auto n=1+(b.bytes-e.offset-12)/b.stride;if(!n||n>65536)return;
 for(unsigned i=0;i<n;i++){float v[3];memcpy(v,b.src+i*b.stride+e.offset,12);
 for(unsigned j=0;j<3;j++){if(!(std::abs(v[j])<1e10f))return;if(!i)box[j]=box[3+j]=v[j];else{box[j]=std::min(box[j],v[j]);box[3+j]=std::max(box[3+j],v[j]);}}}
 stage|=4;}
};
static_assert(sizeof(JoinDraw)==288);
'''.replace('OUT',out)+k)
s=rep(s,'    st_.draws++;','    JoinDraw obs{jrender};st_.draws++;')
s=rep(s,'            checked_rigid=true;','''            checked_rigid=true;if(obs.id){obs.stage=1;unsigned n=0;for(auto t:{256,2,3}){memcpy(obs.mats+n,s.transforms[t].data(),64);n+=16;}memcpy(obs.clip,rigid_clip,64);obs.bounds(a);}''')
s=rep(s,'                ++rigid_skipped_;','                obs.stage|=2;++rigid_skipped_;')
if parents:
 s=rep(s,'if(fwrite(this,sizeof(*this),1,fp)!=1)', 'if(fwrite(this,8,1,fp)!=1)')
 s=rep(s,'obs.bounds(a);','')
if bindings:
 k2='    if (a.index_count) {\n        d_.vkCmdBindIndexBuffer'
 s=rep(s,k2,r"""
    // Record the final bindings after any ring rollover, immediately before the game draw.
    {static uint64_t serial; ++serial;if(obs.id){
      uint64_t row[]={obs.id,serial,ring_epoch_,vc,dc,(uint64_t)pipe,
      (uint64_t)img[0].imageView,(uint64_t)img[1].imageView,(uint64_t)img[2].imageView,(uint64_t)img[3].imageView,
      (uint64_t)smp[0].sampler,(uint64_t)smp[1].sampler,(uint64_t)smp[2].sampler,(uint64_t)smp[3].sampler};
      static FILE *fp=fopen("OUTbindings.bin","wb");if(fwrite(row,sizeof row,1,fp)!=1)std::abort();}}
""".replace('OUT',out)+k2)
p.link[p.link.index(str(REGS/'backend-host-clip.o'))]=p.compile('vk/backend.cpp',s,['-DNGB_RIGID_CLIP'])
s=(RUNTIME/'scene/bridge.c').read_text()
for k,f in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
 s=rep(s,k,k+'extern void jflip(unsigned);jflip('+f+');'+('if(scene_flips==124)ngb_stop("finished joined opening",124);' if f!='0' else ''))
p.add('scene/bridge.c',s)
s=(REGS/'host-driver.c').read_text().replace('ngb_stop("verified 120 original demo frames", 120);','fprintf(stderr,"[JOIN] original opening motion verified at 120\\n");')
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',s,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
p.link.insert(1,'-Wl,--strip-debug');p.finish()
