// Rehashes and direct-cache collisions must not lose the latest usage fence.
// Live changes to Data/Parent and later reuse of a header are also observable.
struct NativeHeaderProbe {
    std::mutex mutex;
    std::condition_variable changed;
    unsigned entered=0,allow=0,seen=0;
    bool correct=true;
    uint32_t data=0;
};
class NativeHeaderBackend final : public gpu::Backend {
    NativeHeaderProbe& probe;
public:
    explicit NativeHeaderBackend(NativeHeaderProbe& p):probe(p){}
    bool Init(uint32_t,uint32_t) override { return true; }
    void Clear(const gpu::State& s,uint32_t,const uint8_t*,uint32_t,uint32_t index,float,uint32_t) override {
        if(index==0 || index==81) {
            std::unique_lock lock(probe.mutex);
            probe.entered=index==0?1:2;probe.changed.notify_all();
            probe.changed.wait(lock,[&]{return probe.allow>=probe.entered;});
        }
        unsigned slot=index<80?index:index==80?1:0;
        gpu::TextureDesc d;
        probe.correct &= gpu::Describe(s.rt.header,d) &&
            (d.data&0x0fffffff)==probe.data+slot*256 &&
            d.width==(index==81?16u:8u) && d.height==(index==81?2u:4u) &&
            R32(d.data)==0x12340000u+slot;
        ++probe.seen;
    }
    void Draw(const gpu::State&,uint32_t,uint32_t,uint32_t,const uint8_t*,const gpu::IndexBounds*,gpu::CombatEffect) override {}
    void Copy(const gpu::Surface&,const gpu::Surface&,uint32_t,const uint8_t*,const uint8_t*) override {}
    void Present(const gpu::Surface&) override {}
    void Sync(uint32_t,uint32_t) override {}
    void SyncLate(uint32_t) override {}
    void Flush() override {}
    void SetGamma(const uint8_t*) override {}
};

void NativeHeaderContract() {
    auto require=[](bool okay,uint32_t detail){if(!okay)ngb_stop("native header tracking failed",detail);};
    uint32_t headers=NativePool(8192),data=NativeData(80*256),parent_a=headers+6144,parent_b=headers+6208,alias=headers+6272;
    for(unsigned i=0;i<80;++i) {
        uint32_t h=headers+i*64;
        W32(h,0x50001);W32(h+4,data+i*256);W32(h+12,0x11221);W32(h+16,7|(3<<12));W32(h+20,parent_a);
        W32((data+i*256)|0x80000000u,0x12340000u+i);
    }
    for(uint32_t h:{parent_a,parent_b,alias}) {W32(h,0x40001);W32(h+4,data);}
    NativeHeaderProbe probe;probe.data=data;
    g_backend=gpu::CreateThreadedBackend(std::make_unique<NativeHeaderBackend>(probe));
    require(g_backend->Init(8,4),1);
    auto record=[&](uint32_t header,unsigned index){
        gpu::State state{};state.rt=SurfaceOf(header);
        g_backend->Clear(state,0,nullptr,gpu::kClearTarget,index,1,0);
    };
    auto entered=[&](unsigned phase){
        std::unique_lock lock(probe.mutex);
        require(probe.changed.wait_for(lock,std::chrono::seconds(2),[&]{return probe.entered==phase;}),2+phase);
    };
    auto release=[&](unsigned phase){std::lock_guard lock(probe.mutex);probe.allow=phase;probe.changed.notify_all();};
    record(headers,0);g_backend->Fence();entered(1);
    for(unsigned i=1;i<80;++i)record(headers+i*64,i);
    W32(headers+4,data+256);W32(headers+20,parent_b);record(headers,80);g_backend->Fence();
    W32(headers+4,data);W32(headers+16,15|(1<<12));record(headers,81);
    uint32_t last=g_backend->Fence();
    release(1);entered(2);
    require(g_backend->Busy(headers) && g_backend->Busy(alias) && g_backend->Busy(parent_b),5);
    // The queued final command owns a header copy even if the caller reuses it.
    std::memset(HostPtr(headers,24),0xcc,24);
    release(2);g_backend->WaitFence(last);
    require(probe.correct && probe.seen==82 && !g_backend->Busy(alias),6);
    g_backend.reset();
    require(ngb_contiguous_free(data|0x80000000u),7);ngb_graphics_pool_free(headers);
    std::fprintf(stderr,"[CONTRACT-PASS] header-cache-collisions rehash inline-data-parent-changes latest-batch alias-wait header-reuse\n");
}
