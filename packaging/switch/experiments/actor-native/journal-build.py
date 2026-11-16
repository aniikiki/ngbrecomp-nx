"""Timestamp worker writes at private polls, then replay to actual IRQ times.
Uses compiler-instrumented stores only in this offline verifier."""
from pathlib import Path
s=Path(__file__).with_name('checkpoint-build.py').read_text()
a=s.index("exec(compile(s,'checkpoint-worker'")
pre=s[:a].replace("d=p/'opt050/actor-checkpoints'","d=p/'opt050/actor-journal'")
exec(compile(pre,'worker-trace-generator','exec'))
s=s.replace('unsigned stride,events;', 'unsigned stride,events,nlog,pending,width;uint32_t *log;')
s=s.replace('static inline void ngb_guest_block_poll(void){','''static void flush_store(void){
 if(!ac.width)return;
 if(ac.nlog+ac.width>524288){ac.error=~0u;longjmp(ac.unwind.escape,1);}
 for(unsigned k=0;k<ac.width;k++){unsigned a=ac.pending+k;
  uint32_t *e=ac.log+3*ac.nlog++;e[0]=ac.events;e[1]=a;e[2]=ac.ram[a];}
 ac.width=0;}
static inline void ngb_guest_block_poll(void){flush_store();''')
s=s.replace('unsigned *events){','unsigned *events,uint32_t *log,unsigned *nlog){ac.log=log;ac.nlog=ac.width=0;')
s=s.replace('*events=ac.events;return 0;','flush_store();*nlog=ac.nlog;*events=ac.events;return 0;')
# GCC instruments lvalues and memcpy builtins; capture values after the
# actual store by draining on the next store/poll. Calls to plain memcpy
# may bypass hooks: a mismatch is not safe to publish.
insert=s.index("code+=''.join('static void clone_")
s=s[:insert]+"code+='static __attribute__((no_sanitize_thread)) void observe_store(void*,unsigned);\\nstatic __attribute__((no_sanitize_thread)) void* journal_copy(void*d,const void*s,size_t n){observe_store(d,n);return __builtin_memcpy(d,s,n);}\\nstatic __attribute__((no_sanitize_thread)) void* journal_set(void*d,int v,size_t n){observe_store(d,n);return __builtin_memset(d,v,n);}\\n'\n"+s[insert:]
s=s.replace(' srcs[va]=src\ncode+='," src=src.replace(' memcpy(', ' journal_copy(').replace(' memset(', ' journal_set(')\n srcs[va]=src\ncode+=")
a=s.index("f=d/'actor.c'")
s=s[:a]+'''code+=r"""
#define NOINST __attribute__((no_sanitize_thread))
static NOINST void observe_store(void*p,unsigned n){
 uintptr_t a=(uintptr_t)p-(uintptr_t)ac.ram;if(a>=(128u<<20)||n>(128u<<20)-a)return;
 flush_store();ac.pending=a;ac.width=n;
}
#define HOOK(N) NOINST void __tsan_read##N(void*p){} NOINST void __tsan_write##N(void*p){observe_store(p,N);} \\
 NOINST void __tsan_read_write##N(void*p){observe_store(p,N);} NOINST void __tsan_unaligned_read##N(void*p){} \\
 NOINST void __tsan_unaligned_write##N(void*p){observe_store(p,N);}
HOOK(1) HOOK(2) HOOK(4) HOOK(8) HOOK(16)
NOINST void __tsan_init(void){}
NOINST void __tsan_read_range(void*p,unsigned long n){}
NOINST void __tsan_write_range(void*p,unsigned long n){observe_store(p,n);}
"""
'''+s[a:]
s=s.replace('static void flush_store(void)', 'static __attribute__((no_sanitize_thread)) void flush_store(void)')
s=s.replace("cmd.insert(-1,'-g0')","cmd[1:1]=['-fsanitize=thread','--param=tsan-instrument-func-entry-exit=0'];cmd.insert(-1,'-g0')")
# Rename worker hooks after assembly, or linking would steal the original
# reference observer's sanitizer entry points.
s+="\nsymbols=sp.check_output([nm,'--defined-only',o],text=True);syms=[x.split()[-1] for x in symbols.splitlines() if '__tsan_' in x];sp.run(['/opt/devkitpro/devkitA64/bin/aarch64-none-elf-objcopy',*['--redefine-sym='+x+'=private_'+x for x in syms],o],check=True)\n"
if '--touch' in __import__('sys').argv:
 s=s.replace("d=p/'opt050/actor-journal'","d=p/'opt050/actor-touch'")
 s=s.replace('return (uintptr_t)ac.ram+a;', 'return (uintptr_t)ac.ram+a;')
 i=s.index("mem=mem[:a]+")
 # Memory helpers are above generated definitions. Track potentially mutable
 # scalar or vector spans until the next poll; compare the true bytes there.
 s=s[:i]+s[i:].replace('static __attribute__((no_sanitize_thread)) void flush_store(void){', 'static void touch_drain(void);\nstatic __attribute__((no_sanitize_thread)) void flush_store(void){',1)
 s=s.replace('ngb_guest_block_poll(void){flush_store();', 'ngb_guest_block_poll(void){flush_store();touch_drain();')
 s=s.replace('static inline uintptr_t ngb_guest_scalar(uint32_t a,size_t n){','static void touch_add(uint32_t,size_t);\nstatic inline uintptr_t ngb_guest_scalar(uint32_t a,size_t n){touch_add(a,n);')
 s=s.replace('unsigned stride,events,nlog,','unsigned nt;uint32_t touch[1024];uint8_t prior[1024][4];unsigned stride,events,nlog,')
 s=s.replace('ac.trace=trace;','ac.nt=0;ac.trace=trace;')
 code="""
static __attribute__((no_sanitize_thread)) void touch_add(uint32_t a,size_t n){
 a&=0x7fffffff;if(a>=(128u<<20)||!n||n>(128u<<20)-a)return;
 for(uint32_t w=a&~3u;w<=a+n-1;w+=4){
  unsigned j=0;while(j<ac.nt && ac.touch[j]!=w)j++;
  if(j==ac.nt){if(j==1024){ac.error=~0u;longjmp(ac.unwind.escape,1);}ac.nt++;ac.touch[j]=w;__builtin_memcpy(ac.prior[j],ac.ram+w,4);}
 }}
static __attribute__((no_sanitize_thread)) void touch_drain(void){
 for(unsigned j=0;j<ac.nt;j++){uint32_t w=ac.touch[j];
  for(unsigned k=0;k<4;k++)if(ac.ram[w+k]!=ac.prior[j][k]){
   if(ac.nlog==524288){ac.error=~0u;longjmp(ac.unwind.escape,1);}uint32_t*e=ac.log+3*ac.nlog++;e[0]=ac.events;e[1]=w+k;e[2]=ac.ram[w+k];
  }}ac.nt=0;}
"""
 i=s.index("code+=''.join('static void clone_");s=s[:i]+'code+='+repr(code)+'\n'+s[i:]
 s=s.replace('flush_store();*nlog','flush_store();touch_drain();*nlog')
exec(compile(s,'worker-journal','exec'))
