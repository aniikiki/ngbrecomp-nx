"""Build a Switch-targeted, reentrant copy of observed actor math/logic.
Only verified plain memory and recognized game functions are allowed.
Unsupported functions, unmapped I/O or cross-page accesses cancel that job.
Never fall through into the shared game register file, kernel or graphics."""
from pathlib import Path
import subprocess as sp,re,shlex,sys
p=Path('/work/build/switch-runtime');d=p/'opt050/actor-native';d.mkdir(exist_ok=True);g=p/'gen';w=p/'switch';r=Path('/work/packaging/switch/runtime')
targets={line.split()[0] for line in Path(sys.argv[1]).read_text().splitlines()};targets.update(('001482B0','00147F10','00148120'))
srcs={}
for f in sorted(g.glob('recomp_*.c')):
 for m in re.finditer(r'^void (sub_|d3d_orig_)([0-9A-F]+)\(void\)\n\{.*?^\}',f.read_text(),re.M|re.S):
  if m[2] in targets:srcs[m[2]]=m.group()
assert targets==set(srcs),targets-set(srcs)
# Honor inline helpers in recomp_types.h, even before the generated functions.
# Local preprocessor mappings bind every path to per-thread storage.
prefix='''#include <stdint.h>
#include <setjmp.h>
#include "switch_guest_regs.h"
static _Thread_local struct actor_state {
 RecompRegs regs;unsigned char *ram;const uint16_t *pages;uint64_t polls,entries;
 unsigned pc,error; union { jmp_buf escape; unsigned char reserved[1024]; } unwind;
} ac;
#undef RECOMP_REGS
#define RECOMP_REGS ac.regs
'''
mem=(r/'guest_memory.h').read_text();a=mem.index('extern uint64_t ngb_guest_polls;');b=mem.index('#ifdef __SWITCH__\n#pragma GCC visibility pop',a)
mem=mem[:a]+'''#define ngb_guest_polls ac.polls
#define ngb_pending_dpcs 0u
#define ngb_poll_mask 63u
#define ngb_fast_page_bytes ac.pages
#define ngb_fast_ram ac.ram
#define NGB_RAM_BYTES (64u<<20)
static inline void ngb_guest_block_poll(void){++ac.polls;}
static inline int ngb_static_image_span(uint32_t a,size_t n){return __builtin_constant_p(a) && a>=0x8000 && a<0x1000000 && n<=0x1000000-a;}
static inline void *ngb_ram_span(uint32_t a,size_t n){if(n<=4096u-(a&4095u) && (a&4095u)+n<=ac.pages[a>>12])return ac.ram+(a&0x7fffffffu);return 0;}
static inline void *ngb_guest_vector_page(uint32_t a){return ngb_ram_span(a,16);}
static inline void actor_bail(unsigned e){ac.error=e;longjmp(ac.unwind.escape,1);}
static inline uintptr_t ngb_guest_scalar(uint32_t a,size_t n){
 if(ngb_static_image_span(a,n))return (uintptr_t)ac.ram+a;
 void*p=ngb_ram_span(a,n);if(!p)actor_bail(a);return (uintptr_t)p;}
#define ngb_guest_pointer(a,n) ngb_guest_scalar((a),(n))
static inline void ngb_vector_read_slow(uint32_t a,uint32_t v[4]){(void)v;actor_bail(a);}
static inline void ngb_vector_write_slow(uint32_t a,const uint32_t v[4]){(void)v;actor_bail(a);}
'''+mem[b:];(d/'guest_memory.h').write_text(mem)
# Use identical headers, but resolve guest_memory.h within the worker directory.
for f in ['recomp_types.h','recomp_funcs.h']:(d/f).write_text((g/f).read_text())
code=prefix+'\n#define RECOMP_GENERATED_CODE\n#include "recomp_funcs.h"\n#include "arm_math.h"\n#include "matrix.h"\n#include <math.h>\n'
code+='''
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) do{ ++ac.entries;ac.pc=(va);ngb_guest_block_poll(); }while(0)
static void actor_dispatch(unsigned va);
#undef RECOMP_ABI_CALL
#define RECOMP_ABI_CALL(va,fn) actor_dispatch(va)
#undef RECOMP_ICALL_SAFE_AT
#define RECOMP_ICALL_SAFE_AT(va,sp,site) actor_dispatch(va)
#undef RECOMP_ITAIL
#define RECOMP_ITAIL(va) actor_dispatch(va)
#undef RECOMP_UNIMPL
#define RECOMP_UNIMPL(msg,pc) actor_bail(pc)
#undef __debugbreak
#define __debugbreak() actor_bail(ac.pc)
'''
for va,src in srcs.items():
 name=re.match(r'void (\w+)',src)[1];src=src.replace('void '+name+'(void)','static void clone_'+va+'(void)',1)
 # Compile-time direct calls stay direct; never bind an external game symbol.
 src=re.sub(r'RECOMP_ABI_CALL\(0x([0-9A-F]+)u, (?:sub_|d3d_orig_)[0-9A-F]+\)',lambda m:'clone_'+m[1]+'()' if m[1] in targets else 'actor_bail(0x'+m[1]+'u)',src)
 src=re.sub(r'\b(?:sub_|d3d_orig_)([0-9A-F]+)\(\)',lambda m:'clone_'+m[1]+'()' if m[1] in targets else 'actor_bail(0x'+m[1]+'u)',src)
 srcs[va]=src
code+=''.join('static void clone_'+a+'(void);\n' for a in srcs)
code+='\n'.join(srcs.values())
code+='\nstatic void actor_dispatch(unsigned va){switch(va){'+''.join('case 0x'+a+':clone_'+a+'();break;' for a in srcs)+'default:actor_bail(va);}}\n'
code+='''
unsigned ngb_actor_native(void *result,unsigned char *ram,const uint16_t *pages,uint64_t *polls,uint64_t *entries){
 memcpy(&ac.regs,result,sizeof ac.regs);ac.ram=ram;ac.pages=pages;ac.polls=*polls;ac.entries=0;ac.error=0;
 if(setjmp(ac.unwind.escape))return ac.error?ac.error:~0u;
 g_esi=MEM32(g_esp+20);PUSH32(g_esp,g_edi);PUSH32(g_esp,g_esi);PUSH32(g_esp,0x147ed8);clone_001482B0();
 PUSH32(g_esp,g_esi);PUSH32(g_esp,0x147ede);clone_00147F10();
 PUSH32(g_esp,g_esi);g_eax=g_edi;PUSH32(g_esp,0x147ee6);clone_00148120();
 memcpy(result,&ac.regs,sizeof ac.regs);*polls=ac.polls;*entries=ac.entries;return 0;
}
'''
f=d/'actor.c';f.write_text(code);cmd=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if x.endswith('/recomp_0010.c'))
o=str(d/'actor.o');cmd[cmd.index('-o')+1]=o;cmd[cmd.index('-MF')+1]=o+'.d';cmd[-1]=str(f);cmd[1:1]=['-I'+str(d),'-I'+str(r)];cmd.insert(-1,'-g0');sp.run(cmd,cwd=w,check=True)
nm='/opt/devkitpro/devkitA64/bin/aarch64-none-elf-nm';print('worker functions',len(srcs),flush=True);undefined=sp.check_output([nm,'-u',o],text=True);print(undefined)
for sym in re.findall(r'\bU (\S+)',undefined):
 if sym not in {'setjmp','_setjmp','longjmp','memcpy','memset','memmove','memcmp','sqrt','sqrtf','sin','cos','atan2','sinf','cosf','atan2f','fmod','exp2','frexp','ldexp','__aarch64_read_tp'}:raise ValueError('Worker may touch shared game state: '+sym)
