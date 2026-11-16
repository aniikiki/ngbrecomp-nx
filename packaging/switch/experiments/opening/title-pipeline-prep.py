"""Host-only comparison. Keep synchronous first-use fallback on every miss."""
def apply(s):
    def after(k,v):
        nonlocal s
        assert s.count(k)==1,k
        s=s.replace(k,k+v)
    after('    CacheOpen();','\n    if (std::getenv("NGB_OPEN_WARM_PIPELINES")) Prewarm();')
    after('    presents_++;', r"""
    if(recipes_ && (presents_==1 || presents_==30 || presents_==120) && std::getenv("NGB_OPEN_RECIPE_CENSUS"))
        std::fprintf(stderr,"[RECIPE_EXTENT] %u %ld\n",presents_,std::ftell(recipes_));
""")
    after('    presents_++;', r"""
    static const bool count_first_use=std::getenv("NGB_OPEN_COUNT_CREATES")!=nullptr;
    if(count_first_use && presents_<=120){
        static uint64_t use_us;static unsigned made_s,made_p;
        use_us+=compile_us_;made_s+=compiles_;made_p+=pipes_made_;
        if(presents_==1 || presents_==30 || presents_==120)
            std::fprintf(stderr,"[OPEN_CREATES] present=%u shader=%u pipeline=%u us=%llu\n",presents_,made_s,made_p,(unsigned long long)use_us);
    }
""")
    import sys, runpy
    if '--recipe-sources' in sys.argv:
        a=s.index('void VulkanBackend::Prewarm()')
        t=s[a:]; key='            VkShaderModule m = Compile(hlsl, vertex, spirv) ? MakeModule(spirv) : VK_NULL_HANDLE;'
        assert t.count(key)==1
        t=t.replace(key,key+"""
            if(m) std::fprintf(stderr,"[RECIPE_SOURCE] %c %016llx %016llx %zu\\n",r.kind,
                    (unsigned long long)r.key,(unsigned long long)Hash(hlsl.data(),hlsl.size(),vertex?0x5653ull:0x5053ull),spirv.size());""")
        return s[:a]+t
    if '--recipe-retry' in sys.argv:
        from pathlib import Path
        return runpy.run_path(str(Path(__file__).with_name('recipe-retry.py')))['inject'](s)
    return s


def instrument_first_use(s):
    def sub(a,b):
        nonlocal s
        assert s.count(a)==1,a
        s=s.replace(a,b)
    k='    VkShaderModule MakeModule('
    sub(k,'    uint64_t src_ns_=0, spv_ns_=0, mod_ns_=0, pipe_ns_=0, seen_mod_=0, seen_pipe_=0;\n'+k)
    k='    std::string hlsl = src();'
    sub(k,'    auto source_begin=std::chrono::steady_clock::now();\n'+k+
        '\n    ++seen_mod_; src_ns_+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-source_begin).count();')
    k='    VkShaderModule m = Compile(hlsl, vertex, spirv) ? MakeModule(spirv) : VK_NULL_HANDLE;\n    {'
    sub(k,"""    bool compiled=Compile(hlsl, vertex, spirv);
    auto split=std::chrono::steady_clock::now();
    spv_ns_+=std::chrono::duration_cast<std::chrono::nanoseconds>(split-t0).count();
    VkShaderModule m=compiled ? MakeModule(spirv) : VK_NULL_HANDLE;
    mod_ns_+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-split).count();
    {""")
    k='        if (d_.vkCreateGraphicsPipelines(dev_, pcache_, 1, &ci, nullptr, &pipe) != VK_SUCCESS) pipe = VK_NULL_HANDLE;'
    sub(k,'        auto native_begin=std::chrono::steady_clock::now();\n'+k+
        '\n        ++seen_pipe_; pipe_ns_+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-native_begin).count();')
    k='    presents_++;'
    sub(k,k+r"""
    if(presents_==1 || presents_==30 || presents_==120)
        std::fprintf(stderr,"[COLD_COST] frame=%u modules=%llu pipes=%llu source_ns=%llu spirv_ns=%llu module_ns=%llu pipeline_ns=%llu\n",presents_,(unsigned long long)seen_mod_,(unsigned long long)seen_pipe_,(unsigned long long)src_ns_,(unsigned long long)spv_ns_,(unsigned long long)mod_ns_,(unsigned long long)pipe_ns_);
""")
    return s
