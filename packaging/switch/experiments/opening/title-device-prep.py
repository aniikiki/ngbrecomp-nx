"""Diagnostic only: time creation of the offscreen device separately at title idle.
Do not publish the prepared device to the game until Start's normal 3D path.
"""
def install(p,s,background=False):
 h=(p.out/'hle.cpp').read_text()
 k='bool g_started;';assert h.count(k)==1
 h=h.replace(k,k+'''
static std::unique_ptr<gpu::Backend> idle_device;
extern "C" int opening_prepare_device(void){
    if (ngb_scene_active || g_backend || idle_device) return 0;
    auto device=gpu::CreateBackend();
    if (!device || !device->Init(640,480)) return 0;
    idle_device=std::move(device);
    return 1;
}
''')
 if background:
  h='#include <pthread.h>\n#include <chrono>\n'+h
  a=h.index('extern "C" int opening_prepare_device(void)')
  b=h.index('\n}',a)+2
  h=h[:a]+r'''static pthread_t idle_worker;
static bool idle_launched;
using IdleClock=std::chrono::steady_clock;
static long long idle_ns(IdleClock::time_point t) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(IdleClock::now()-t).count();
}
static void* idle_create(void*) {
    auto t=IdleClock::now();
    auto device=gpu::CreateBackend();
    if (device && device->Init(640,480)) idle_device=std::move(device);
    std::fprintf(stderr,"[IDLE_WORKER] ready=%d work_ns=%lld\n",int(bool(idle_device)),idle_ns(t));
    return nullptr;
}
extern "C" int opening_prepare_device(void){
    if (ngb_scene_active || g_backend || idle_launched) return 0;
    idle_launched=pthread_create(&idle_worker,nullptr,idle_create,nullptr)==0;
    return idle_launched;
}
static void idle_finish(){
    if (!idle_launched) return;
    auto t=IdleClock::now();
    pthread_join(idle_worker,nullptr);
    idle_launched=false;
    std::fprintf(stderr,"[IDLE_WORKER] join_ns=%lld\n",idle_ns(t));
}'''+h[b:]
 k='    g_backend = gpu::CreateBackend();\n    if (g_backend && !g_backend->Init(640, 480))'
 assert h.count(k)==1
 h=h.replace(k,'''    bool prepared=bool(idle_device);
    g_backend = prepared ? std::move(idle_device) : gpu::CreateBackend();
    if (prepared) std::fprintf(stderr,"[IDLE_DEVICE] adopted at scene start\\n");
    if (g_backend && !prepared && !g_backend->Init(640, 480))''')
 k='    g_backend.reset();\n    ngb_render_threaded = 0;';assert h.count(k)==1
 if background:
  h=h.replace('    bool prepared=bool(idle_device);','    idle_finish();\n    bool prepared=bool(idle_device);')
 p.compile('hle.cpp',h.replace(k,('    idle_finish();\n' if background else '')+'    idle_device.reset();\n'+k))
 # The benchmark disables surface readback; use the real overlay initialization
 # notification that both the wide replay and the device log emit.
 k='    __real_ngb_kernel_log(message);';assert s.count(k)==1
 return s.replace(k,k+"""
 static unsigned prep_attempted;
 if (!prep_attempted && !strncmp(message,"Main menu overlay renderer=",sizeof("Main menu overlay renderer=")-1)) {
   prep_attempted=1;
   extern int opening_prepare_device(void);
   uint64_t start=ngb_elapsed_ns();int ready=opening_prepare_device();
   fprintf(stderr,"[IDLE_DEVICE] ready=%d elapsed_ns=%llu\\n",ready,(unsigned long long)(ngb_elapsed_ns()-start));
 }""")
