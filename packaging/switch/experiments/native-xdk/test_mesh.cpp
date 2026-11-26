// Reuse the material test's memory/device model; compare whole mesh outputs,
// draw-time states and effect ordering with the extracted original function.
#define main existing_material_test
#include "test_material.cpp"
#undef main
#include <cmath>

Xmm xmm1;
Xmm XMM_ZERO() { return {{0,0,0,0}}; }
double g_fp_stack[8]; unsigned g_fp_top;
#define RECOMP_FP_PC(v) double(float(v))
#define g_esp esp
#define CMP_A(a,b) ((a)>(b))
#define CMP_AE(a,b) ((a)>=(b))
#define CMP_B(a,b) ((a)<(b))
#define CMP_BE(a,b) ((a)<=(b))
#define CMP_LE(a,b) ((a)<=(b))
#define RECOMP_SPIN(a) ((void)0)
#define SET_LO8(a,b) ((a)=((a)&0xffffff00u)|uint8_t(b))
#define SMEM8(a) int8_t(MEM8(a))
#define SX8(a) uint32_t(int32_t(int8_t(a)))
#define ZX8(a) uint32_t(uint8_t(a))
uint64_t ngb_guest_polls;
unsigned ngb_poll_mask=~0u, ngb_pending_dpcs;
static void (*observe_poll)(uint64_t);
void ngb_poll_due(uint64_t ticket) { if (observe_poll) observe_poll(ticket); }
static void reference_model_poll() {
    uint64_t ticket = ++ngb_guest_polls;
    if (!(ticket & ngb_poll_mask) || ngb_pending_dpcs) ngb_poll_due(ticket);
}
void ngb_direct_mesh_scope(int) {}
void ngb_d3d_mesh_scope(int) {}
static unsigned model_depth;
unsigned ngb_d3d_model_suspend() {
    unsigned previous = model_depth;
    model_depth = 0;
    native_mesh_coherent = false;
    return previous;
}
void ngb_d3d_model_resume(unsigned previous) {
    model_depth = previous;
    native_mesh_coherent = false;
}
int ngb_d3d_mesh_allowed(uint32_t a) { return MEM32(a+8)<=4; }
uint32_t ngb_native_mesh_enabled=1;
int ngb_direct_material_fixed() { material::Fixed(esi); esp+=4;return 1; }
int ngb_direct_material_texture() { material::Texture(eax,edi);esp+=4;return 1; }
int ngb_d3d_mesh_fixed(uint32_t a,uint32_t slot) { return material::PrepareMesh(a,slot); }
int ngb_d3d_mesh_texture(unsigned s,uint32_t a) { if(s>=4)return 0;material::Texture<true>(s,a);return 1; }
void sub_0036FDB8() { eax=uint32_t(int32_t(std::trunc(g_fp_stack[g_fp_top])));g_fp_top=(g_fp_top+1)&7;esp+=4; }

struct Event {
    uint32_t kind,a,b,c;
    bool operator==(const Event& o) const { return kind==o.kind&&a==o.a&&b==o.b&&c==o.c; }
};
std::vector<Event> events;
std::vector<gpu::State> draws;
void SyncState() {
    std::memcpy(g_state.rs.data()+92,HostPtr(kRenderState+92*4),(gpu::kRsMax-92)*4);
    for(unsigned s=0;s<4;++s) std::memcpy(g_state.tss[s].data(),HostPtr(kTextureState+s*128),22*4);
    std::memcpy(g_state.material.data(),HostPtr(kNativeDevice+0xf00),17*4);
    for(unsigned t=0;t<10;++t) std::memcpy(g_state.transforms[t<2?t+2:t<6?t+14:t+250].data(),HostPtr(kNativeDevice+0xc60+t*64),64);
}
void draw(uint32_t kind,uint32_t n,uint32_t p) {
    SyncState(); events.push_back({kind,n,p,0});draws.push_back(g_state);
}
void sub_003CAFC0() {draw(0,MEM32(esp+4),0);esp+=12;}
void sub_003C9B40() {draw(1,MEM32(esp+8),MEM32(esp+12));esp+=16;}
void sub_003C5630() {Complex(148);}
static unsigned callback_depth;
void effect(uint32_t target,uint32_t before,uint32_t site) {
    // Different callback kinds deliberately mutate both material cache and
    // deferred state, and observe the mesh pointer passed by the original.
    events.push_back({target,MEM32(esp+4),before-esp,site});
    if (site == 0x0030C332u) {
        callback_depth = model_depth;
        // A guest callback can replace its argument before the decoder pops it.
        eax ^= target;
        MEM32(esp + 4) ^= 0x4242;
        esp += 4;
        return;
    }
    MEM32(kRenderState+100*4)^=target;
    MEM32(0x44b500)+=target;
    esp+=4;
}
#define RECOMP_ICALL_SAFE_AT(t,b,s) effect(t,b,s)
#include "reference_callback.inc"
void sub_0030C2A0() {
    if (MEM8(eax + 1) == 10 && MEM32(0x30c360) == 0x0030c32e) {
        reference_callback();
        return;
    }
    events.push_back({0xff,MEM32(eax+4),MEM32(eax+8),0});
    MEM32(kRenderState+99*4)=MEM32(eax+8);esp+=4;
}
void sub_0030C370() {
    events.push_back({eax,MEM32(ecx+4),MEM32(ecx+8),0});
    MEM32(kRenderState+98*4)=MEM32(ecx+8);esp+=4;
}
void sub_0030C240();
// Even an empty command list reaches the guest scheduler. Compare every
// checkpoint with the generated routine, including its position around a draw.
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) do { if ((va) == 0x0030C240u) \
    events.push_back({(va), eax, uint32_t(draws.size()), uint32_t(bindings.size())}); } while (0)
#include "reference_mesh.inc"

// Exercise the same state setters as the player, including its warm material path.
#include "mesh_setters.inc"
void ngb_d3d_mesh_draw(uint32_t a) {
    if(!MEM32(a+0x1c)) return;
    uint32_t kind=MEM32(a+0x10),data=MEM32(a+0x14);
    if(!kind) draw(0,data,0);
    else draw(1,MEM32(a+0x18)/2,kind==1?MEM32(data+4)+12:MEM32(MEM32(MEM32(a+4)+0x18)+4)+data);
}
#define ngb_guest_block_poll reference_model_poll
#include "../../runtime/direct/native_mesh.inc"
#undef ngb_guest_block_poll
uint16_t ngb_fast_page_bytes[1u<<20];
uint8_t* ngb_fast_ram=memory.data();
void sub_0030C1A0() {events.push_back({0x30c1a0,eax,0,0});esp+=4;}
void ngb_d3d_model_scope(int enter) { model_depth += enter ? 1 : -1; }
void ngb_d3d_model_world(uint32_t m) {
    MEM32(0x977bd4)=m;
    for(unsigned i=0;i<16;++i) MEM32(kNativeDevice+0xde0+i*4)=MEM32(m+i*4);
    MEM32(0x3d83d0)|=0x200;
}
#define ngb_guest_block_poll reference_model_poll
#include "reference_model.inc"
#undef ngb_guest_block_poll
#include "../../runtime/direct/native_model.inc"

#include "test_model_lights.inc"
#include "test_render_list.inc"

static void test_texture_stage_poll() {
    constexpr uint32_t mat = 0x1200000, vertex = mat + 0x1000, commands = mat + 0x200;
    for (unsigned mode = 0; mode < 3; ++mode) {
        for (auto r : ranges) std::memset(HostPtr(r.start, r.size), 0, r.size);
        g_state = {}; g_df = 0; native_mesh_coherent = false;
        W32(kDevicePtr, kNativeDevice); W32(mat + 4, vertex); W32(mat + 8, 1);
        W32(mat + 0x64, 0x1201800); W32(0xc0ebb0, 1); MEMF(0x4148c8) = 1;
        material::Fixed<true>(mat); material::Texture<true>(0, mat + 0x60);
        if (!material::PrepareMesh(mat, top - 64)) std::abort();
        esp = top; PUSH32(esp, 0x3f800000); PUSH32(esp, commands); PUSH32(esp, mat); PUSH32(esp, 0);
        ngb_poll_mask = 7; ngb_guest_polls = mode == 1 ? 7 : 0; ngb_pending_dpcs = mode == 2;
        observe_poll = [](uint64_t) { W32(mat + 0x64, 0x1201a00); };
        if (!ngb_direct_mesh() || g_state.textures[0] != (mode ? 0x1201a00u : 0x1201800u) ||
            esp != top - 12 || ngb_guest_polls != (mode == 1 ? 8u : 1u)) std::abort();
        observe_poll = nullptr;
    }
    ngb_pending_dpcs = 0;
}

static void test_mesh_callback() {
    constexpr uint32_t node = 0x1201000, arg = node + 0x100, stack = 0x3000000;
    MEM8(node + 1) = 10;
    MEM32(0x30c360) = 0x0030c32e;
    for (unsigned mode = 0; mode < 8; ++mode) {
        uint32_t target = mode == 0 ? 0x001d7800 : mode == 7 ? 0x003173b0 : 0x00127290;
        MEM32(node + 4) = target; MEM32(node + 8) = mode == 1 ? 0 : arg;
        MEM16(arg + 0x222) = mode == 3 ? 4 : 6;
        MEM16(arg + 0x224) = mode == 4 ? 0 : 2;
        MEM8(arg + 0x22b) = mode == 5;
        ngb_guest_polls = 7; ngb_poll_mask = mode == 6 ? 7 : 63;
        auto run = [&](bool native) {
            events.clear(); model_depth = 2; native_mesh_coherent = true;
            esp = stack; eax = node; ecx = 0xabcdef; esi = 0x12345;
            std::memset(HostPtr(stack - 16, 16), 0xab, 16);
            if (native) mesh_global_command();
            else {
                PUSH32(esp, 0x0030C27Du);
                reference_callback();
            }
            return std::array<uint32_t,8>{eax,ecx,esi,esp,MEM32(stack-4),MEM32(stack-8),
                                           MEM32(stack-12),MEM32(stack-16)};
        };
        auto expected = run(false); auto calls = events;
        if (run(true) != expected || calls != events || model_depth != 2 ||
            callback_depth != (mode <= 2 ? 2u : 0u) || native_mesh_coherent != (mode <= 2))
            std::abort();
    }
    MEM32(0x30c360) = 0; model_depth = 0;
}

int main() {
    test_mesh_callback();
    test_model_lights();
    test_render_list();
    test_model_polls();
    test_texture_stage_poll();
    std::mt19937 rng(0x577);
    constexpr uint32_t mat=0x1200000,vertex=mat+0x1000,cmds=mat+0x100,lists=mat+0x1800;
    for(unsigned test=0;test<12000;++test) {
        ngb_poll_mask = test % 3 ? 63 : 3;
        ngb_guest_polls = test;
        for(auto r:ranges) std::memset(HostPtr(r.start,r.size),0,r.size);
        g_state=gpu::State{};bindings.clear();events.clear();draws.clear();native_mesh_coherent=false;
        MEM32(kDevicePtr)=kNativeDevice;MEM32(mat+4)=vertex;
        MEM32(mat+8)=test%5;MEM32(mat+0x20)=(test/5)%2;
        MEM32(mat+0x38)=(test/10)%2?0x302:1;
        MEM32(0xc0ebb0)=3;MEMF(0x4148c8)=1;MEMF(0x41494c)=1;MEMF(0x414920)=255;
        MEMF(mat+0x6c)=.75f;MEM32(vertex)=2;MEM32(vertex+8)=0x1210000;MEM32(vertex+0x10)=32;
        MEM32(vertex+0x18)=vertex+0x40;MEM32(vertex+0x44)=0x1220000;
        MEM32(mat+0x10)=(test/20)%3;MEM32(mat+0x14)=vertex+0x80;
        MEM32(vertex+0x84)=0x1230000;MEM32(mat+0x18)=48;MEM32(mat+0x1c)=test%7!=0;
        for(unsigned s=0;s<4;++s) {
            MEM32(0x977968+s*4)=0x100+s;MEM32(kNativeDevice+0xf88+s*4)=0x100+s;
        }
        // Alternating no-list, built-in, one-argument and two-argument callbacks.
        for(unsigned pass=0;pass<3;++pass) {
            uint32_t p=lists+pass*32;MEM32(cmds+pass*4)=test%3?p:0;
            MEM8(p)=test%4<2?0xfe:test%4==2?0xff:2;MEM8(p+1)=test%2?10:11;
            MEM32(p+4)=0x555+pass;MEM32(p+8)=0x777+pass;
        }
        if(test%5) {MEM8(mat+0x50)=1;MEM8(mat+0x51)=2;MEM32(0x44b414)=0x111;MEM32(0x44b42c)=0x222;}
        float alpha=test%6==0?0:test%6==1?-.1f:test%6==2?.4f:1;
        MEM32(0xc05fcc)=test%11==0;MEMF(0x44b438)=alpha;
        if (test % 13 == 0) {
            // Lit meshes, attached callbacks and bindings which can release a
            // guest resource also occur between these otherwise compatible draws.
            MEM32(mat+8)=1;MEM32(mat+0x20)=0;MEM32(mat+0x38)=0x302;MEM32(mat+0x3c)=1;
            MEM8(mat+0x50)=0;MEM32(vertex)=0x142;MEM32(mat+0x64)=0x1210200;
            std::memset(HostPtr(cmds,12),0,12);MEM32(0xc05fcc)=0;
            unsigned used=alpha<1?2:1;MEM32(0xc0ebb0)=used;MEM32(0x977968+used*4)=0;
            MEM32(0x3d93b0)=MEM32(vertex+8);
            MEM32(0x977968)=MEM32(kNativeDevice+0xf88)=MEM32(mat+0x64);
        }
        esp=0x3000000;ebx=0xaaaa;esi=0xbbbb;edi=0xcccc;g_seh_ebp=0xdddd;
        PUSH32(esp,0);MEMF(esp)=alpha;PUSH32(esp,cmds);PUSH32(esp,mat);PUSH32(esp,0);
        uint32_t entry=esp;
        Snapshot before;
        sub_0030BCA0();SyncState();Snapshot expected;auto eb=bindings;auto ee=events;auto ed=draws;
        if(esp!=entry+4||ebx!=0xaaaa||esi!=0xbbbb||edi!=0xcccc) std::abort();
        before.Restore();esp=entry;ebx=0xaaaa;esi=0xbbbb;edi=0xcccc;
        // The alpha argument can be changed by the override path.
        MEMF(entry+12)=alpha;bindings.clear();events.clear();draws.clear();
        if(!ngb_direct_mesh()) std::abort();SyncState();Snapshot actual;
        bool same=actual.bytes==expected.bytes&&bindings==eb&&events==ee&&draws.size()==ed.size();
        for(unsigned i=0;i<draws.size()&&i<ed.size();++i) same &= !std::memcmp(&draws[i],&ed[i],sizeof(gpu::State));
        if(!same||esp!=entry+4||ebx!=0xaaaa||esi!=0xbbbb||edi!=0xcccc) {
            std::fprintf(stderr,"FAIL mesh %u memory=%d bindings=%d events=%d draws=%zu/%zu\n",test,actual.bytes!=expected.bytes,bindings!=eb,events!=ee,draws.size(),ed.size());
            size_t offset=0;for(auto r:ranges){for(unsigned j=0;j<r.size;++j)if(actual.bytes[offset+j]!=expected.bytes[offset+j]){std::fprintf(stderr,"memory %x actual %u expected %u\n",r.start+j,actual.bytes[offset+j],expected.bytes[offset+j]);goto found;}offset+=r.size;}found:;
            return 1;
        }
        // Model traversal: multiple meshes, pass filtering, temporary callback
        // list linking, world transforms and both early-out LOD branches.
        for(unsigned filtered=0;filtered<2;++filtered) {
            constexpr uint32_t model=mat+0x1100,matrix=mat+0x1400,descriptor=mat+0x1500;
            MEM32(model+8)=3;MEM32(model+0x94)=MEM32(model+0xb4)=MEM32(model+0xd4)=mat;
            MEM8(model+0x91)=0;MEM8(model+0xb1)=1;MEM8(model+0xd1)=0;
            for(unsigned j=0;j<16;++j) MEMF(matrix+j*4)=float(j+test%17);
            MEM32(0xd21e48)=test%9==0?4:1;MEM32(0xd21e40)=test%2?3:1;
            MEM32(descriptor)=0xffffffff;MEM32(descriptor+4)=lists;MEM32(descriptor+12)=lists+32;
            MEM32(descriptor+8)=lists+64;MEM32(descriptor+16)=descriptor+32;
            MEM32(descriptor+32)=1;MEM32(descriptor+36)=lists;MEM32(descriptor+40)=lists+32;
            MEM32(descriptor+44)=lists+64;MEM32(descriptor+48)=0;
            // Keep the transient joined lists acyclic.
            MEM32(lists+76)=0;
            esp=0x3000000;ebx=0xaaaa;esi=0xbbbb;edi=0xcccc;eax=matrix;
            PUSH32(esp,0);MEMF(esp)=alpha;
            if(filtered) PUSH32(esp,test%2);
            PUSH32(esp,test%3?descriptor:0);PUSH32(esp,model);PUSH32(esp,0);
            uint32_t start=esp;
            Snapshot input;bindings.clear();events.clear();draws.clear();
            if(filtered) sub_00307A10();else sub_003078B0();
            SyncState();Snapshot want;auto wb=bindings;auto we=events;auto wd=draws;
            input.Restore();esp=start;ebx=0xaaaa;esi=0xbbbb;edi=0xcccc;eax=matrix;
            bindings.clear();events.clear();draws.clear();
            if(filtered)ngb_direct_model_filtered();else ngb_direct_model();
            SyncState();Snapshot got;
            bool equal=want.bytes==got.bytes&&bindings==wb&&events==we&&draws.size()==wd.size();
            for(unsigned j=0;j<draws.size()&&j<wd.size();++j)equal &= !std::memcmp(&draws[j],&wd[j],sizeof(gpu::State));
            if(!equal||esp!=start+4||ebx!=0xaaaa||esi!=0xbbbb||edi!=0xcccc){
                std::fprintf(stderr,"FAIL model %u filtered %u memory=%d bindings=%d events=%d draws=%zu/%zu stack=%x/%x\n",test,filtered,got.bytes!=want.bytes,bindings!=wb,events!=we,draws.size(),wd.size(),esp,start+4);
                return 1;
            }
        }
    }
    std::puts("PASS: 12000 mesh + 24000 model comparisons: alpha, callbacks, state, resources, draw order and preserved registers");
}
