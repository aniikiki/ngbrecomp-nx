"""Timestamp synchronous HLE startup and the first flips; no renderer changes."""
from pathlib import Path
def install(p,src):
 s=(Path('/work')/'src/d3d/hle.cpp').read_text()
 k='    g_backend = gpu::CreateBackend();';assert s.count(k)==1
 s='extern "C" void init_probe(unsigned);\n'+s.replace(k,'    init_probe(0);\n'+k)
 k='    // Graphics > Multithreaded Renderer';assert s.count(k)==1
 s=s.replace(k,'    init_probe(1);\n'+k)
 k='    std::fprintf(stderr, "[D3D] renderer on';assert s.count(k)==1
 p.add('hle.cpp',s.replace(k,'    init_probe(2);\n'+k))
 return src.replace('void __real_ngb_kernel_log',r'''
static unsigned init_frame,init_count;
static uint64_t init_base[2],init_last[2],init_start[2];
static uint64_t init_clock(int cpu){struct timespec ts;
 if(clock_gettime(cpu?CLOCK_THREAD_CPUTIME_ID:CLOCK_MONOTONIC,&ts))abort();
 return (uint64_t)ts.tv_sec*1000000000ull+ts.tv_nsec;}
void init_probe(unsigned stage){
 uint64_t w=init_clock(0),c=init_clock(1);
 if(!stage){init_start[0]=w;init_start[1]=c;init_count++;}
 fprintf(stderr,"[INIT_STAGE] %u %u %u %llu %llu\n",init_count,init_frame,stage,(unsigned long long)(w-init_start[0]),(unsigned long long)(c-init_start[1]));}
void phase_flip(unsigned f){
 uint64_t w=init_clock(0),c=init_clock(1);
 if(!f){init_base[0]=w;init_base[1]=c;}
 else if(f<=4||f==30||f==120){fprintf(stderr,"[FIRST_INIT] %u %llu %llu %llu %llu\n",f,(unsigned long long)(w-init_last[0]),(unsigned long long)(c-init_last[1]),(unsigned long long)(w-init_base[0]),(unsigned long long)(c-init_base[1]));}
 init_frame=f+1;init_last[0]=w;init_last[1]=c;}
void __real_ngb_kernel_log''',1)
