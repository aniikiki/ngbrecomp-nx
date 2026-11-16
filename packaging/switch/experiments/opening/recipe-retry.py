"""Replay only: reject alternate prewarm creations, observe successful first use by exact key."""
def inject(s):
    k='    void Prewarm();'
    assert s.count(k)==1
    s=s.replace(k,k+'''
    std::unordered_map<uint64_t,bool> failed_m;
    std::unordered_map<PipeKey,bool,PipeHash> failed_p;
    unsigned tries_m=0,tries_p=0;
''')
    a=s.index('void VulkanBackend::Prewarm()');b=s.index('void VulkanBackend::WarmSamples',a)
    t=s[a:b]
    for k,expr in [('VkPipeline p = MakePipeline(k, vs, ps);',
                    'VkPipeline p = (++tries_p%2) ? (failed_p[k]=true,VK_NULL_HANDLE) : MakePipeline(k,vs,ps);'),
                   ('VkShaderModule m = Compile(hlsl, vertex, spirv) ? MakeModule(spirv) : VK_NULL_HANDLE;',
                    'VkShaderModule m = (++tries_m%2) ? (failed_m[r.key]=true,VK_NULL_HANDLE) : (Compile(hlsl,vertex,spirv)?MakeModule(spirv):VK_NULL_HANDLE);')]:
        assert t.count(k)==1
        t=t.replace(k,expr)
    s=s[:a]+t+s[b:]
    for function,key,handle,field in [('Module','key','m','failed_m'),('Pipeline','k','pipe','failed_p')]:
        a=s.index('VulkanBackend::'+function+'(');b=s.index('\n}',a)
        k='return '+handle+';'
        assert s[a:b].count(k)==1
        s=s[:a]+s[a:b].replace(k,'if ('+handle+' && '+field+'.erase('+key+')) std::fprintf(stderr,"[RECIPE_RETRY] '+function+' recovered\\n");\n    '+k)+s[b:]
    return s
