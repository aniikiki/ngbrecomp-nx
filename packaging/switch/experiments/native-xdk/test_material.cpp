#include <array>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <random>
#include <unordered_map>
#include <vector>
#include "gpu/state.h"
#include "gpu/prepared.h"

static std::vector<uint8_t> memory(64 * 1024 * 1024);
void* HostPtr(uint32_t a, size_t n = 4) {
    if (uint64_t(a) + n > memory.size()) std::abort();
    return memory.data() + a;
}
#define MEM32(a) (*static_cast<uint32_t*>(HostPtr(uint32_t(a))))
#define MEM8(a) (*static_cast<uint8_t*>(HostPtr(uint32_t(a), 1)))
#define MEMF(a) (*static_cast<float*>(HostPtr(uint32_t(a))))
uint32_t R32(uint32_t a) { return MEM32(a); }
void W32(uint32_t a, uint32_t v) { MEM32(a) = v; }
constexpr uint32_t kRenderState = 0x3d83d8, kTextureState = 0x3d5d10;
constexpr uint32_t kDevicePtr = 0x3d83c8, kNativeDevice = 0x2000000;
gpu::State g_state;
bool native_mesh_coherent;
uint32_t native_mesh_changed;
std::unordered_map<uint32_t, std::shared_ptr<gpu::VertexShader>> g_vs;
std::vector<std::array<uint32_t, 2>> bindings;
void NativeBind(uint32_t old, uint32_t next) { bindings.push_back({old, next}); }
void NativeFlush() {}
enum { ND_STATE };
struct NativeDiagScope { explicit NativeDiagScope(unsigned) {} };
#include "native_material.inc"

uint32_t eax, ecx, edx, ebx, esp, esi, edi, g_ebp, g_seh_ebp, g_df;
union Xmm { float f[4]; } xmm0;
Xmm XMM_SCALAR(float f) { return {{f,0,0,0}}; }
#define RECOMP_ENTRY(a) ((void)0)
#define RECOMP_ABI_CALL(a,f) f()
#define PUSH32(s,v) do { (s) -= 4; MEM32(s) = (v); } while (0)
#define POP32(s,v) do { (v) = MEM32(s); (s) += 4; } while (0)
#define CMP_EQ(a,b) ((a)==(b))
#define CMP_NE(a,b) ((a)!=(b))
#define CMP_L(a,b) ((a)<(b))
#define HI8(a) (((a)>>8)&255)
#define LO8(a) ((a)&255)
#define RECOMP_PARITY8(a) (!__builtin_parity(unsigned(uint8_t(a))))
void ngb_guest_block_poll() {}
void* ngb_guest_pointer(uint32_t a, size_t n) { return HostPtr(a,n); }
void* ngb_ram_span(uint32_t a, size_t n) { return HostPtr(a,n); }
void sub_0030D630();
void sub_003C9030() {
    uint32_t shader = MEM32(esp+4); W32(kNativeDevice+0x794, shader);
    g_state.vs_handle = shader; g_state.vs.reset();
    if (shader&1) { auto it = g_vs.find(shader); if (it!=g_vs.end()) g_state.vs=it->second; }
    esp+=8;
}
void sub_003C8710() {
    uint32_t stride=MEM32(esp+4);
    NativeBind(MEM32(0x3d93b0),ebx); MEM32(0x3d93b0)=ebx; MEM32(0x3d93a8)=stride;
    g_state.streams[0]={ebx,stride}; esp+=8;
}
void Complex(unsigned state) {
    uint32_t v=MEM32(esp+4); MEM32(kRenderState+state*4)=v; g_state.rs[state]=v; esp+=8;
}
void sub_003C5340() { Complex(147); }
void sub_003C5BE0() { Complex(137); }
void sub_003C5500() { Complex(144); }
void sub_003C5460() { Complex(143); }
void sub_003C5C60() {
    g_state.simple[(ecx&0x1ffc)/4]=edx;
    switch(ecx&0x1ffc) {
    case 0x304: MEM32(0x3d84c4)=edx; break;
    case 0x340: MEM32(0x3d84cc)=edx; break;
    case 0x344: MEM32(0x3d84d0)=edx; break;
    case 0x348: MEM32(0x3d84d4)=edx; break;
    case 0x34c: MEM32(0x3d8504)=edx; break;
    case 0x368: MEM32(0x3d84f4)=edx; break;
    case 0x35c: MEM32(0x3d84d8)=edx; break;
    default: std::abort();
    }
    esp+=4;
}
void sub_003C79A0() {
    uint32_t handle=MEM32(esp+4), slot=kNativeDevice+0xf88+eax*4;
    NativeBind(MEM32(slot),handle); MEM32(slot)=handle; g_state.textures[eax]=handle; esp+=8;
}
void sub_003C5C90() {
    uint32_t value=MEM32(esp+4); MEM32(kTextureState+esi*128+28*4)=value;
    g_state.tss[esi][gpu::kTssTexCoordIndex]=value; esp+=8;
}
void sub_003C7160() {
    std::memcpy(HostPtr(kNativeDevice+0xc60+eax*64,64),HostPtr(edx,64),64);
    std::memcpy(g_state.transforms[eax+14].data(),HostPtr(edx,64),64); esp+=4;
}
#include "reference.inc"

struct Range { uint32_t start, size; };
const Range ranges[]={{0x977000,4096},{0x3d5000,0x5000},{kNativeDevice,0x2000},
                      {0x44b000,4096},{0x1200000,0x2000},{0xc05000,4096},{0xc0e000,4096}};
struct Snapshot {
    std::vector<uint8_t> bytes;
    gpu::State state;
    Snapshot() : state(g_state) {
        for(auto r:ranges) {
            const auto* data=static_cast<uint8_t*>(HostPtr(r.start,r.size));
            bytes.insert(bytes.end(),data,data+r.size);
        }
    }
    void Restore() const {
        size_t n=0;
        for(auto r:ranges) { std::memcpy(HostPtr(r.start,r.size),bytes.data()+n,r.size); n+=r.size; }
        g_state=state; bindings.clear();
    }
};
void Reference(uint32_t address) {
    esp=0x3000000; esi=address; PUSH32(esp,0); sub_0030B7E0();
    uint32_t count=MEM32(address+8);
    edi=address+0x60+(MEM32(address+0x20)?0x50:0);
    for(unsigned stage=0;stage<count;++stage,edi+=0x40) {
        eax=stage; PUSH32(esp,0); sub_0030BA30();
    }
    if(esp!=0x3000000) std::abort();
}
int main() {
    std::mt19937 random(0x30bca0);
    constexpr uint32_t address=0x1200000, vertex=0x1201000;
    for(unsigned test=0;test<20000;++test) {
        for(auto r:ranges) for(unsigned i=0;i<r.size;i+=4) MEM32(r.start+i)=random();
        MEM32(kDevicePtr)=kNativeDevice; MEM32(address+4)=vertex;
        MEM32(address+8)=test%5; MEM32(address+0x20)=(test/5)%2;
        MEM32(0x44b3c0)=test%3; MEM32(vertex)=(test%3)*2;
        // Include +/-zero, infinities and NaNs, plus the ordinary changed case.
        const uint32_t floats[]={0,0x80000000,0x3f800000,0x7f800000,0xff800000,0x7fc00001};
        for(unsigned i=0;i<17;++i) {
            MEM32(address+0x60+i*4)=floats[random()%6];
            MEM32(0x977b78+i*4)=test%3?MEM32(address+0x60+i*4):floats[random()%6];
        }
        // Alternating fresh and repeated material application exercises cache hits.
        if(test&1) Reference(address);
        Snapshot before; bindings.clear(); Reference(address);
        Snapshot expected; auto expected_bindings=bindings;
        before.Restore();
        if(!material::Submit(address)) std::abort();
        Snapshot actual;
        if(actual.bytes!=expected.bytes || bindings!=expected_bindings ||
           std::memcmp(&actual.state,&expected.state,sizeof(gpu::State))) {
            for(size_t i=0;i<actual.bytes.size();++i) if(actual.bytes[i]!=expected.bytes[i]) {
                size_t n=i; uint32_t a=0; for(auto r:ranges) { if(n<r.size) {a=r.start+n;break;} n-=r.size; }
                std::fprintf(stderr,"case %u: memory %08x actual=%02x expected=%02x\n",test,a,actual.bytes[i],expected.bytes[i]);break;
            }
            std::fprintf(stderr,"FAIL case %u state=%d bindings=%d\n",test,
                std::memcmp(&actual.state,&expected.state,sizeof(gpu::State)),bindings!=expected_bindings);
            return 1;
        }
    }
    MEM32(address+8)=5; Snapshot before;
    if(material::Submit(address) || Snapshot().bytes!=before.bytes) std::abort();
    std::puts("PASS: 20000 generated-reference material comparisons; invalid count leaves state untouched");
    return 0;
}
