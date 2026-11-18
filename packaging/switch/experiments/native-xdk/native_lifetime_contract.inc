// A deliberately stalled renderer proves that destroying a view may return
// before replay, while destroying the last owner must keep its data alive.
struct NativeLifetimeProbe {
    std::mutex mutex;
    std::condition_variable changed;
    bool entered=false,allow=false,released=false,rescued=false,correct=false;
    uint32_t data=0;
};
class NativeHeldBackend final : public gpu::Backend {
    NativeLifetimeProbe& probe;
public:
    explicit NativeHeldBackend(NativeLifetimeProbe& p):probe(p){}
    bool Init(uint32_t,uint32_t) override { return true; }
    void Clear(const gpu::State& s,uint32_t,const uint8_t*,uint32_t,uint32_t,float,uint32_t) override {
        std::unique_lock lock(probe.mutex); probe.entered=true; probe.changed.notify_all();
        probe.changed.wait(lock,[&]{return probe.allow;});
        gpu::TextureDesc d;
        probe.correct=gpu::Describe(s.rt.header,d) && (d.data&0x0fffffff)==probe.data &&
            d.width==8 && d.height==4 && R32(d.data)==0x12345678;
    }
    void Draw(const gpu::State&,uint32_t,uint32_t,uint32_t,const uint8_t*,const gpu::IndexBounds*) override {}
    void Copy(const gpu::Surface&,const gpu::Surface&,uint32_t,const uint8_t*,const uint8_t*) override {}
    void Present(const gpu::Surface&) override {}
    void Sync(uint32_t,uint32_t) override {}
    void SyncLate(uint32_t) override {}
    void Flush() override {}
    void SetGamma(const uint8_t*) override {}
};

void NativeLifetimeContract(uint32_t scratch) {
    auto require=[](bool okay,uint32_t detail){if(!okay)ngb_stop("native resource lifetime failed",detail);};
    NativeLifetimeProbe probe;
    g_backend=gpu::CreateThreadedBackend(std::make_unique<NativeHeldBackend>(probe));
    require(g_backend->Init(8,4),1);
    for (bool owned_header : {false,true}) for (bool last_parent : {false,true}) {
        uint32_t texture=NativeHeader(20);
        uint32_t bytes=NativeTextureHeader(8,4,1,1,6,0,false,false,texture+12,texture+16);
        uint32_t data=NativeData(bytes); W32(texture,0x01040001); W32(texture+4,data); W32(data|0x80000000u,0x12345678);
        uint32_t view=owned_header?NativeHeader(24):scratch+256;
        W32(view,owned_header?0x01050001:0x00050001); W32(view+4,data); W32(view+8,0);
        W32(view+12,R32(texture+12)); W32(view+16,R32(texture+16)); W32(view+20,texture);
        NativeAddRef(texture); if(last_parent)NativeRelease(texture);
        {
            std::lock_guard lock(probe.mutex);
            probe.entered=probe.allow=probe.released=probe.rescued=probe.correct=false; probe.data=data;
        }
        gpu::State state{}; state.rt=SurfaceOf(view);
        g_backend->Clear(state,0,nullptr,gpu::kClearTarget,0,1,0);
        uint32_t fence=g_backend->Fence();
        {
            std::unique_lock lock(probe.mutex);
            require(probe.changed.wait_for(lock,std::chrono::seconds(2),[&]{return probe.entered;}),2);
        }
        uint64_t epoch=gpu::DirtyEpoch(data|0x80000000u);
        std::thread release_gate([&]{
            std::unique_lock lock(probe.mutex);
            bool returned=probe.changed.wait_for(lock,last_parent?std::chrono::milliseconds(30):
                std::chrono::milliseconds(2000),[&]{return probe.released;});
            probe.rescued=!last_parent && !returned;
            probe.allow=true; probe.changed.notify_all();
        });
        NativeRelease(view);
        bool early;
        {
            std::lock_guard lock(probe.mutex);
            early=!probe.allow;
            // A caller-owned temporary header can immediately be reused.
            if(!owned_header)std::memset(HostPtr(view,24),0xcd,24);
            probe.released=true; probe.changed.notify_all();
        }
        release_gate.join();
        g_backend->WaitFence(fence);
        require(!probe.rescued && probe.correct && early!=last_parent,3);
        if(!last_parent) {
            require(R32(texture)==0x01040001 && gpu::DirtyEpoch(data|0x80000000u)==epoch,4);
            NativeRelease(texture);
        }
    }
    g_backend.reset();
    std::fprintf(stderr,"[CONTRACT-PASS] view-release-with-pending-replay header-reuse parent-data-lifetime dirty-epoch\n");
}
