#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>
#include "gpu/state.h"

std::vector<uint32_t> memory(0x400000 / 4);
constexpr uint32_t kRenderState = 0x3d83d8, kSimpleEncode = 0x3e9278;
unsigned encoding_reads;
void* HostPtr(uint32_t address) { return memory.data() + address / 4; }
uint32_t R32(uint32_t address) {
    if (address >= kSimpleEncode && address < kSimpleEncode + 92 * 4) ++encoding_reads;
    return memory.at(address / 4);
}
void W32(uint32_t address, uint32_t value) { memory.at(address / 4) = value; }
gpu::State g_state;
extern "C" { uint32_t ngb_native_mesh_enabled = 1; }
#include "native_simple.inc"
#include "reference_simple.inc"
const uint32_t real_table[] = {
#include "real-table.inc"
};

int main() {
    std::mt19937 rng(577);
    unsigned cases = 0;
    for (unsigned layout = 0; layout < 32; ++layout) {
        for (unsigned i = 0; i < 92; ++i) {
            uint32_t value = !layout ? real_table[i] : layout == 1 ? 0x40300 :
                layout == 2 ? 0 : (rng() & ~0x1ffcu) | ((rng() % 2048) * 4);
            W32(kSimpleEncode + i * 4, value);
        }
        native_simple_ready = false;
        for (unsigned j = 0; j < 2052; ++j) {
            uint32_t method = j < 2048 ? j * 4 : j == 2048 ? 0x2000 :
                j == 2049 ? 0x2004 : j == 2050 ? 0xffffffffu : 3;
            for (unsigned i = 0; i < 166; ++i) W32(kRenderState + i * 4, rng());
            for (auto& value : g_state.simple) value = rng();
            auto before = g_state.simple;
            std::array<uint32_t,166> initial, expected;
            std::memcpy(initial.data(), HostPtr(kRenderState), sizeof initial);
            uint32_t value = rng();
            NativeSimpleReference(method, value);
            auto simple = g_state.simple;
            std::memcpy(expected.data(), HostPtr(kRenderState), sizeof expected);
            g_state.simple = before;
            std::memcpy(HostPtr(kRenderState), initial.data(), sizeof initial);
            unsigned reads = encoding_reads;
            NativeSimple(method, value);
            assert(g_state.simple == simple);
            assert(!std::memcmp(expected.data(), HostPtr(kRenderState), sizeof expected));
            assert(encoding_reads - reads == (j == 0 ? 92 : 0));
            ++cases;
        }
        for (auto& value : g_state.simple) value = rng();
        auto before = g_state.simple;
        NativeSyncSimpleReference();
        auto expected = g_state.simple;
        g_state.simple = before;
        NativeSyncSimple();
        assert(g_state.simple == expected);
    }
    std::printf("PASS: %u simple-state comparisons plus hydration; actual XBE table, duplicate/zero encodings, all methods, invalid methods, no repeated table reads\n", cases);
}
