"""Record compact workload fingerprints at actual HLE Presents. Do not wrap service calls."""
from pathlib import Path
def install(p,rt,src):
 obj=str(p.out/'hle.cpp.o')
 # Preserve the retained arm's HLE transformations when instrumenting it.
 patched=obj in p.link
 h=(p.out/'hle.cpp' if patched else rt.parents[2]/'src/d3d/hle.cpp').read_text()
 draw='    if (measure) ngb_direct_draw_time'
 swap='        if (g_backend) g_backend->Present(g_state.rt);'
 assert h.count(draw)==h.count(swap)==1
 h='''extern "C" void pm_present(unsigned, unsigned long long,unsigned long long);
static unsigned pm_n;
static unsigned long long pm_volume,pm_sig=14695981039346656037ull;
'''+h.replace(draw,'''    ++pm_n; pm_volume+=count;
    pm_sig=(pm_sig^((unsigned long long)prim<<32|start))*1099511628211ull;
    pm_sig=(pm_sig^((unsigned long long)count<<1|!!indices))*1099511628211ull;
'''+draw).replace(swap,'''        if(g_backend){pm_present(pm_n,pm_volume,pm_sig);pm_n=0;pm_volume=0;pm_sig=14695981039346656037ull;}
'''+swap)
 if patched:p.compile('hle.cpp',h)
 else:p.add('hle.cpp',h)
 k='void angle_boundary(unsigned f, unsigned draws) {'
 assert src.count(k)==1
 return src.replace(k,'''static unsigned pm_active,pm_fifo,pm_prev_f;static uint64_t pm_prev_cpu,pm_prev_e,pm_prev_p;
void pm_present(unsigned draws,unsigned long long volume,unsigned long long sig){
 if(!pm_active){pm_prev_cpu=0;return;}
 struct timespec ts;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&ts))abort();
 uint64_t now=(uint64_t)ts.tv_sec*1000000000u+ts.tv_nsec;
 if(pm_prev_cpu)fprintf(stderr,"[PRESENT_MIX] %u %u %u %llu %016llx %llu %llu %llu\\n",pm_prev_f,pm_fifo,draws,volume,sig,
 (unsigned long long)(now-pm_prev_cpu),(unsigned long long)(entries-pm_prev_e),(unsigned long long)(ngb_guest_polls-pm_prev_p));
 pm_prev_cpu=now;pm_prev_e=entries;pm_prev_p=ngb_guest_polls;pm_prev_f=pm_fifo;
}
'''+k+'\n    pm_active=f<120;pm_fifo=f;')
