from pathlib import Path
import tempfile,subprocess,runpy
d=Path(__file__).parent
s=runpy.run_path(str(d/'guard-view.py'))['allocator']()+'''
#include <assert.h>
#include <sys/wait.h>
#include <signal.h>
#include <sys/resource.h>
uint32_t opening_end4[1<<20];
void *__real_calloc(size_t n,size_t m){return calloc(n,m);}
void __real_free(void*p){free(p);}
static int fault(uint32_t a){pid_t p=fork();assert(p>=0);if(!p){*(volatile uint32_t*)(guard_active+a)=55;_exit(0);}int st;assert(waitpid(p,&st,0)==p);return WIFSIGNALED(st)&&WTERMSIG(st)==SIGSEGV;}
int main(void){struct rlimit lim={0,0};setrlimit(RLIMIT_CORE,&lim);
uint8_t *canonical=__wrap_calloc(1,span);
opening_end4[2]=12285;opening_end4[0x80002]=0x80002ffdu;guard_flip(0);
assert(fault(4096)&&fault(0x80001000)&&fault(0xfffffffcu));
guard_active[8192]=91;assert(canonical[8192]==91 && guard_active[bias+8192]==91);
opening_end4[2]=0;guard_update(2);assert(fault(8192));assert(!fault(0x80002000));
opening_end4[2]=12285;guard_update(2);assert(!fault(8192));assert(canonical[8192]==55);
guard_flip(120);__wrap_free(canonical);return 0;}
'''
with tempfile.TemporaryDirectory() as t:
 p=Path(t)/'check.c';p.write_text(s);subprocess.run(['cc','-O2',p,'-o',p.with_suffix('')],check=True);subprocess.run([p.with_suffix('')],check=True)
