"""Build the pipe diagnostic with one reusable title device and a same-NRO A/B switch."""
def hle(s):
    k='std::unique_ptr<gpu::Backend> prologue_backend;'
    assert s.count(k)==1
    s=s.replace(k,k+'''
static std::unique_ptr<gpu::Backend> title_device;
#ifdef NGB_TEXTURE_PRELOAD
extern "C" void ngb_texture_idle_backend(gpu::Backend*);
extern "C" void ngb_texture_title_tick(){
    if(title_device && !ngb_scene_active) ngb_texture_idle_backend(title_device.get());
}
#endif
extern "C" void ngb_prepare_title_device(){
    if(g_backend || prologue_backend || title_device || ngb_scene_active) return;
    auto candidate=gpu::CreateBackend();
    if(candidate && candidate->Init(640,480)) title_device=std::move(candidate);
}
''')
    k='    g_backend = gpu::CreateBackend();\n    if (g_backend && !g_backend->Init(640, 480))'
    assert s.count(k)==1
    s=s.replace(k,'''    bool prepared=bool(title_device);
    g_backend = prepared ? std::move(title_device) : gpu::CreateBackend();
    ngb_kernel_log(prepared ? "3D scene [WARM_ADOPT] title_device=1" : "3D scene [WARM_ADOPT] title_device=0");
    if (g_backend && !prepared && !g_backend->Init(640, 480))''')
    k='    g_backend.reset();\n    ngb_render_threaded = 0;'
    assert s.count(k)==1
    return 'extern "C" void ngb_kernel_log(const char*);\n'+s.replace(k,'    title_device.reset();\n'+k)
def backend(s):
    k='    CacheOpen();'
    assert s.count(k)==1
    s=s.replace(k,k+'''
    if(FILE* flag=std::fopen("sdmc:/switch/ngb-runtime/disable-prewarm.flag","rb")){
        std::fclose(flag);ngb_kernel_log("3D scene [WARM_MODE] enabled=0");
    }else{
        ngb_kernel_log("3D scene [WARM_MODE] enabled=1");
        Prewarm();
    }
''')
    k='    prewarm_done_ = 1;'
    i=s.index(k,s.index('    WarmSamples(uint32_t(ms));',s.index('void VulkanBackend::Prewarm()')))
    return s[:i]+'''    char line[160];
    std::snprintf(line,sizeof line,"3D scene [WARM_DONE] records=%zu modules=%u pipelines=%u",recs.size(),made,pipes);
    ngb_kernel_log(line);
'''+s[i:]
