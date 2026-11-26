// Rehashes and direct-cache collisions must not lose the latest usage fence.
// Live changes to Data/Parent and later reuse of a header are also observable.
struct NativeHeaderProbe {
    std::mutex mutex;
    std::condition_variable changed;
    unsigned entered=0,allow=0,seen=0,draws=0,index_draws=0;
    bool correct=true;
    uint32_t data=0;
};
class NativeHeaderBackend final : public gpu::Backend {
    NativeHeaderProbe& probe;
public:
    explicit NativeHeaderBackend(NativeHeaderProbe& p):probe(p){}
    bool Init(uint32_t,uint32_t) override { return true; }
    void Clear(const gpu::State& s,uint32_t,const uint8_t*,uint32_t,uint32_t index,float,uint32_t) override {
        if (index >= 82) {
            gpu::TextureDesc desc;
            const bool texture = gpu::Describe(s.textures[0], desc);
            probe.correct &= texture == (index == 83 || index == 84);
            if (texture) probe.correct &= desc.width == (index == 83 ? 8u : 16u) && desc.height == 4;
            ++probe.seen;
            return;
        }
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
    void Draw(const gpu::State& s,uint32_t,uint32_t expected,uint32_t count,const uint8_t* indices,const gpu::IndexBounds* bounds,gpu::CombatEffect) override {
        if (indices) {
            probe.correct &= count == 64;
            for (unsigned i = 0; i < count; ++i) {
                uint16_t value;
                std::memcpy(&value, indices + i * sizeof(value), sizeof(value));
                probe.correct &= value == expected + i;
            }
            if (bounds) probe.correct &= bounds->first == expected && bounds->last == expected + count - 1;
            ++probe.index_draws;
            return;
        }
        gpu::TextureDesc d;
        probe.correct &= gpu::Describe(s.textures[0],d) && d.width==(expected & 0xffff);
        if (expected >> 16) probe.correct &= gpu::Describe(s.textures[3],d) && d.width==(expected >> 16);
        else probe.correct &= !s.textures[3];
        ++probe.draws;
    }
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
    W32(headers+4,data+256);record(headers,80);
    // Parent sits outside the serialized five words. Its only use here is
    // this repeated binding inside the same batch, with identical Data.
    W32(parent_b+4,0);W32(headers+20,parent_b);record(headers,80);
    require(g_backend->Busy(parent_b),8);
    g_backend->Fence();
    W32(headers+4,data);W32(headers+16,15|(1<<12));record(headers,81);
    // One address can change from a three-word header into a five-word
    // texture and back while the delayed consumer is on an earlier batch.
    const uint32_t resource = headers + 6336;
    W32(resource + 4, data); W32(resource + 12, 0x11221);
    auto record_resource = [&](unsigned index, uint32_t common, unsigned width) {
        W32(resource, common); W32(resource + 16, (width - 1) | (3 << 12));
        gpu::State state{};
        state.textures[0] = resource;
        g_backend->Clear(state, 0, nullptr, gpu::kClearTarget, index, 1, 0);
    };
    record_resource(82, 0x30001, 4);
    record_resource(83, 0x40001, 8);
    record_resource(84, 0x40001, 16);
    record_resource(85, 0x30001, 4);
    // The first word is on a different page from Data and Format. Rebinding
    // and in-place edits must reach the consumer even while it is stalled.
    uint32_t pages = NativePool(12288);
    uint32_t cross = ((pages + 4095u) & ~4095u) + 4092u;
    gpu::State state{};
    uint64_t revision = 0;
    auto draw = [&](unsigned width,uint32_t changes) {
        g_backend->DrawPrepared(state,1,width,1,nullptr,{++revision,changes});
    };
    using Dirty = gpu::PreparedState;
    W32(cross,0x40001); W32(cross+4,data); W32(cross+12,0x11221); W32(cross+16,7|(3<<12));
    state.textures[0] = cross;
    draw(8,~0u); draw(8,0);
    W32(cross+16,15|(3<<12)); draw(16,Dirty::HeaderWrite(cross));
    W32(resource,0x40001); W32(resource+16,31|(3<<12));
    state.textures[0] = resource;
    draw(32,Dirty::TexturesAndPalettes | Dirty::HeaderBindings | Dirty::HeaderWrite(resource));
    W32(cross+16,63|(3<<12)); draw(32,Dirty::HeaderWrite(cross));
    state.textures[0] = cross;
    draw(64,Dirty::TexturesAndPalettes | Dirty::HeaderBindings | Dirty::HeaderWrite(cross));
    // Return from a primary-only layout to the same secondary binding after
    // an edit while unbound. A binding change alone must capture its new data.
    const uint32_t rebind = Dirty::TexturesAndPalettes | Dirty::HeaderBindings;
    state.textures[3] = resource; draw(64 | (32u << 16), rebind);
    state.textures[3] = 0; draw(64, rebind);
    W32(resource + 16, 15 | (3 << 12));
    state.textures[3] = resource; draw(64 | (16u << 16), rebind);
    // Alternate mutable textures that occupy the same metadata-cache slot.
    uint32_t pool = NativePool(513 * 32), first = 0, second = 0;
    std::array<uint32_t,512> tags{};
    for (unsigned i = 0; !first && i < 513; ++i) {
        uint32_t h = pool + i * 32;
        auto& tag = tags[((h >> 4) ^ (h >> 13) ^ (h >> 21)) & 511];
        if (tag) { first = tag; second = h; }
        else tag = h;
    }
    require(first && second, 10);
    state.textures[3] = 0;
    auto bind_texture = [&](uint32_t h, unsigned width) {
        W32(h,0x40001); W32(h+4,data); W32(h+12,0x11221); W32(h+16,(width-1)|(3<<12));
        state.textures[0] = h; draw(width,rebind);
    };
    bind_texture(first,8); bind_texture(second,16); bind_texture(first,32); bind_texture(second,64);
    // Keep the consumer stalled while two sources share a cache set, one is
    // overwritten within a batch, and a third evicts an old snapshot.
    std::vector<std::array<uint16_t,64>> sources(8192);
    auto set = [](const auto& row) {
        uintptr_t ptr = reinterpret_cast<uintptr_t>(row.data());
        return ((ptr >> 2) ^ (ptr >> 13)) & 1023;
    };
    std::array<uint16_t*,3> collision{};
    unsigned found = 0;
    for (auto& row : sources) {
        if (set(row) != set(sources.front())) continue;
        collision[found++] = row.data();
        if (found == collision.size()) break;
    }
    require(found == collision.size(), 9);
    auto indexed = [&](unsigned which, unsigned value) {
        for (unsigned i = 0; i < 64; ++i) collision[which][i] = uint16_t(value + i);
        g_backend->Draw(state, 3, value, 64, reinterpret_cast<const uint8_t*>(collision[which]));
    };
    indexed(0,10); indexed(1,20); indexed(0,10); indexed(1,20); indexed(0,10);
    indexed(0,30); indexed(0,30); indexed(2,40); indexed(2,40); indexed(1,50);
    g_backend->Fence();
    indexed(0,60); indexed(0,60);
    uint32_t last=g_backend->Fence();
    release(1);entered(2);
    require(g_backend->Busy(headers) && g_backend->Busy(alias) && g_backend->Busy(parent_b),5);
    // The queued final command owns a header copy even if the caller reuses it.
    std::memset(HostPtr(headers,24),0xcc,24);
    release(2);g_backend->WaitFence(last);
    require(probe.correct && probe.seen==87 && probe.draws==13 && probe.index_draws==12 && !g_backend->Busy(alias),6);
    g_backend.reset();
    require(ngb_contiguous_free(data|0x80000000u),7);ngb_graphics_pool_free(headers);ngb_graphics_pool_free(pages);
    ngb_graphics_pool_free(pool);
    std::fprintf(stderr,"[CONTRACT-PASS] header-cache-collisions rehash inline-data-parent-changes latest-batch alias-wait header-reuse\n");
}
