#ifndef NGB_DIAG
#define NGB_DIAG 1
#endif
#include <volk.h>
#include <switch/arm/counter.h>
#include <mutex>
#include <cstdio>
#include <cstdlib>
extern "C" void ngb_kernel_log(const char*);
extern "C" void __real_volkLoadDeviceTable(VolkDeviceTable*,VkDevice);
namespace {
PipeTimeline pt;std::mutex pt_mutex;
PFN_vkCreateGraphicsPipelines real_create;
void edge(bool pipe,bool enter){std::lock_guard lock(pt_mutex);pt.event(armGetSystemTick(),pipe,enter);}
VKAPI_ATTR VkResult VKAPI_CALL traced_create(VkDevice dev,VkPipelineCache cache,uint32_t n,const VkGraphicsPipelineCreateInfo* ci,const VkAllocationCallbacks* alloc,VkPipeline* out){
    edge(true,true);auto result=real_create(dev,cache,n,ci,alloc,out);edge(true,false);return result;
}
}
extern "C" void __wrap_volkLoadDeviceTable(VolkDeviceTable* table,VkDevice dev){
    __real_volkLoadDeviceTable(table,dev);
    if(!NGB_DIAG)return;
    std::lock_guard lock(pt_mutex);
    if(!table->vkCreateGraphicsPipelines || (real_create && real_create!=table->vkCreateGraphicsPipelines))std::abort();
    real_create=table->vkCreateGraphicsPipelines;table->vkCreateGraphicsPipelines=traced_create;++pt.tables;
}
extern "C" void pt_wait(bool enter){if(NGB_DIAG)edge(false,enter);}
extern "C" void pt_flip(unsigned f){
    if(!NGB_DIAG || f>121)return;
    PipeTimeline snapshot;
    {std::lock_guard lock(pt_mutex);
     pt.flip(armGetSystemTick(),f);
     if(f!=121)return;
     snapshot=pt;}
    char line[180];
    for(unsigned i=1;i<=120;i++){auto& b=snapshot.bins[i];
        std::snprintf(line,sizeof(line),"3D scene [PIPE_ATTR] %u %u %u %u %llu %llu %llu",i,b.starts,b.ends,b.calls,
            (unsigned long long)b.wait,(unsigned long long)b.create,(unsigned long long)b.both);ngb_kernel_log(line);}
    std::snprintf(line,sizeof(line),"3D scene [PIPE_ATTR_END] tables=%u bad=%u hz=%llu",snapshot.tables,snapshot.bad,(unsigned long long)armGetSystemTickFreq());ngb_kernel_log(line);
}
