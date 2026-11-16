"""Enumerate future guest-byte readers in the actual isolated worker.
Used to check the effect of intervening fibers, including uninstrumented
native code, by comparing live RAM before/after each due poll."""
from pathlib import Path
here=Path(__file__).resolve().parent
s=(here/'journal-build.py').read_text()
i=s.index("exec(compile(s,'worker-journal'")
s=s[:i]+'''s=s.replace("d=p/'opt050/actor-journal'", "d=p/'opt050/actor-reads'")
s=s.replace('unsigned stride,events,nlog,','uint16_t *last_read;uint32_t *read_list;unsigned nread;unsigned stride,events,nlog,')
s=s.replace('uint32_t *log,unsigned *nlog){','uint32_t *log,unsigned *nlog,uint16_t *last_read,uint32_t *read_list,unsigned *num_read){ac.last_read=last_read;ac.read_list=read_list;ac.nread=0;')
s=s.replace('*nlog=ac.nlog;', '*num_read=ac.nread;*nlog=ac.nlog;')
s=s.replace('#define HOOK(N)',"""static NOINST void observe_read(const void*p,unsigned n){
 uintptr_t a=(uintptr_t)p-(uintptr_t)ac.ram;if(a>=(128u<<20)||n>(128u<<20)-a)return;
 for(unsigned j=0;j<n;j++){if(!ac.last_read[a+j]){if(ac.nread==262144){ac.error=~0u;longjmp(ac.unwind.escape,1);}ac.read_list[ac.nread++]=a+j;}
 ac.last_read[a+j]=ac.events+1;}
}
#define HOOK(N)""")
s=s.replace('__tsan_read##N(void*p){}','__tsan_read##N(void*p){observe_read(p,N);}')
s=s.replace('__tsan_unaligned_read##N(void*p){}','__tsan_unaligned_read##N(void*p){observe_read(p,N);}')
s=s.replace('__tsan_read_write##N(void*p){observe_store','__tsan_read_write##N(void*p){observe_read(p,N);observe_store')
s=s.replace('__tsan_read_range(void*p,unsigned long n){}','__tsan_read_range(void*p,unsigned long n){observe_read(p,n);}')
s=s.replace('void observe_store(void*,unsigned);', 'void observe_read(const void*,unsigned);\\\\nstatic __attribute__((no_sanitize_thread)) void observe_store(void*,unsigned);')
s=s.replace('observe_store(d,n);return __builtin_memcpy','observe_read(s,n);observe_store(d,n);return __builtin_memcpy')
'''+s[i:]
exec(compile(s,'read-worker-generator','exec'))
