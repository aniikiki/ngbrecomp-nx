// Compare the original game function at every scheduler boundary and XDK call.
// A poll can change an upcoming light or the ambient value while the loop runs.
#include "d3d_funcs.h"
static std::vector<uint32_t> light_trace;
static unsigned light_poll_number, light_case;
static constexpr uint32_t light_stack = 0x3001000;

static void trace_light_step(unsigned operation)
{
    light_trace.insert(light_trace.end(), {operation, eax, ecx, edx, ebx, esi, edi, esp,
        MEM32(0x977bd4), MEM32(0x3d83d0), MEM32(0x97789c), MEM32(0x3d85a4)});
    for (unsigned i = 0; i < 4; ++i) {
        uint32_t bits;
        std::memcpy(&bits, &xmm0.f[i], 4);
        light_trace.push_back(bits);
    }
    for (unsigned i = 0; i < 36; ++i) light_trace.push_back(MEM32(light_stack - 136 + 4 * i));
    for (unsigned i = 0; i < 16; ++i) light_trace.push_back(MEM32(kNativeDevice + 0xde0 + 4 * i));
}

static void light_poll()
{
    trace_light_step(0);
    unsigned slot = (light_case + light_poll_number++) % 8;
    if (light_case & 4) {
        MEM32(0x9ac118 + slot * 124) ^= 1;
        MEM32(0x9ac0a4 + slot * 124) ^= 123;
        MEM32(0x9ac480) ^= slot;
    }
}

int d3d_hook(int fn)
{
    trace_light_step(fn);
    if (fn == D3DF_D3DDevice_SetLight) esp += 12;
    else if (fn == D3DF_D3DDevice_LightEnable) esp += 8;
    else std::abort();
    eax = 0;
    return 1;
}

void sub_003C7490() { d3d_hook(D3DF_D3DDevice_SetLight); }
void sub_003C7850() { d3d_hook(D3DF_D3DDevice_LightEnable); }
static bool light_disable_span;
static bool device_lights_disabled;
static int ngb_d3d_lights_already_disabled(unsigned) { return device_lights_disabled; }
static void* light_span(uint32_t a, size_t n) { return light_disable_span ? nullptr : ngb_ram_span(a,n); }
static int ngb_d3d_native_enabled() { return 1; }
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) do { trace_light_step(va); light_poll(); } while (0)
#define ngb_guest_block_poll light_poll
#include "reference_lights.inc"
#undef ngb_guest_block_poll
#define ngb_ram_span light_span
#define mesh_poll light_poll
#include "../../runtime/direct/native_model_lights.inc"
#undef mesh_poll
#undef ngb_ram_span
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) ((void)0)

static void test_model_lights()
{
    std::vector<uint32_t> expected;
    for (light_case = 0; light_case < 2048; ++light_case) {
        for (bool native : {false, true}) {
            std::mt19937 gen(light_case);
            for (auto range : {Range{0x9ac0a0, 8 * 124}, Range{light_stack - 136, 144},
                               Range{0x950140, 64}, Range{kNativeDevice + 0xde0, 64}})
                for (unsigned i = 0; i < range.size; i += 4) MEM32(range.start + i) = gen();
            for (unsigned i = 0; i < 8; ++i) {
                MEM32(0x9ac118 + i * 124) = (light_case >> i) & 1;
                MEM32(0x9ac0a0 + i * 124) = gen() % 4;
            }
            MEM32(kDevicePtr) = kNativeDevice;
            MEM32(0x9ac480) = gen();
            MEM32(0x977bd4) = light_case & 1 ? 0x950140 : 0;
            MEM32(0x97789c) = light_case & 2 ? MEM32(0x9ac480) : 0;
            MEM32(0x3d83d0) = gen(); MEM32(0x3d85a4) = gen();
            esp = light_stack; eax = gen(); ecx = gen(); edx = gen();
            ebx = gen(); esi = gen(); edi = gen(); xmm0 = {{1,2,3,4}};
            light_disable_span = light_case % 7 == 0;
            light_poll_number = 0; light_trace.clear();
            if (native) { if (!ngb_direct_model_lights()) std::abort(); }
            else sub_00317D10();
            trace_light_step(~0u);
            if (!native) expected = light_trace;
            else if (light_trace != expected) {
                auto first = std::mismatch(light_trace.begin(), light_trace.end(), expected.begin(), expected.end());
                std::fprintf(stderr, "model lighting differs in case %u at word %zu\n",
                             light_case, size_t(first.first - light_trace.begin()));
                std::abort();
            }
        }
    }
    for (int offset = -24; offset <= 24; offset += 4) {
        for (bool native : {false, true}) {
            constexpr uint32_t record = 0x9ac0a0;
            for (unsigned i = 0; i < 40; ++i) MEM32(record - 24 + i * 4) = i + 1;
            eax = record + offset; ecx = 0; edx = 0; esp = light_stack;
            xmm0 = {{4,3,2,1}}; light_disable_span = false;
            light_trace.clear(); light_poll_number = 0;
            if (native) model_pack_light(); else sub_00318000();
            trace_light_step(~0u);
            for (unsigned i = 0; i < 40; ++i) light_trace.push_back(MEM32(record - 24 + i * 4));
            if (!native) expected = light_trace;
            else if (light_trace != expected) std::abort();
        }
    }
    // A guest device can alias the identity matrix. rep movsd copies forward
    // even when a destination write overwrites the following source word.
    for (int delta : {-12, 0, 12}) {
        constexpr uint32_t identity = 0x950140;
        for (bool native : {false, true}) {
            for (unsigned i=0; i<24; ++i) MEM32(identity-16+i*4) = i+1;
            for (unsigned i=0; i<8; ++i) MEM32(0x9ac118+i*124) = 0;
            MEM32(kDevicePtr) = identity + delta - 0xde0;
            MEM32(0x977bd4) = 0; MEM32(0x3d83d0) = 0;
            esp = light_stack; light_case = 0; light_poll_number = 0; light_trace.clear();
            if (native) { if (!ngb_direct_model_lights()) std::abort(); }
            else sub_00317D10();
            light_trace.clear();
            for (unsigned i=0; i<24; ++i) light_trace.push_back(MEM32(identity-16+i*4));
            if (!native) expected = light_trace;
            else if (light_trace != expected) std::abort();
        }
    }
    MEM32(kDevicePtr) = kNativeDevice;
    g_df = 1;
    if (ngb_direct_model_lights()) std::abort();
    g_df = 0;
    light_disable_span = false;
    device_lights_disabled = true;
    for (unsigned i = 0; i < 8; ++i) MEM32(0x9ac118 + i * 124) = 0;
    esi = 3; edi = 0x9ac118 + 3 * 124; esp = light_stack;
    MEM32(esp - 8) = 0x00317d81; MEM32(esp - 4) = 0;
    ngb_guest_polls = 0; ngb_poll_mask = 7;
    MEM32(0x9ac118 + 7 * 124) = 1;
    if (finish_disabled_lights()) std::abort();
    MEM32(0x9ac118 + 7 * 124) = 0;
    ngb_pending_dpcs = 1;
    if (finish_disabled_lights()) std::abort();
    ngb_pending_dpcs = 0; ngb_guest_polls = 3;
    if (finish_disabled_lights()) std::abort();
    ngb_guest_polls = 2; MEM32(esp - 4) = 1;
    if (finish_disabled_lights()) std::abort();
    MEM32(esp - 4) = 0;
    if (!finish_disabled_lights() || esi != 8 || edi != 0x9ac4f8 || eax || ngb_guest_polls != 7) std::abort();
    device_lights_disabled = false; ngb_guest_polls = 0; ngb_poll_mask = ~0u;
    std::puts("PASS: 2048 model light submissions, eight slot calls, polls, mutable data, guest stack and registers");
}
