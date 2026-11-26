// The guest memory accessors SCDA-XBERecomp's gpu/ code uses, on this runtime's guest memory
// (recomp_types.h: XBOX_PTR, g_xbox_mem_offset).
#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>

#ifdef NGB_DIRECT3D
extern "C" uintptr_t ngb_guest_pointer(uint32_t, size_t);
extern "C" unsigned char* ngb_direct_pages[];
extern "C" unsigned char** ngb_guest_banks[64];
extern "C" unsigned char ngb_target_pages[];

inline void* DirectPage(uint32_t va, size_t bytes) {
    if (va < (64u << 20) && bytes <= 4096u - (va & 4095u))
        if (auto* page = ngb_direct_pages[va >> 12]) return page + (va & 4095u);
    return nullptr;
}
#else
extern "C" ptrdiff_t g_xbox_mem_offset;
#endif

namespace kernel {
#ifdef NGB_DIRECT3D
inline void* HostPtr(uint32_t va, size_t bytes = 1) {
    if (void* p = DirectPage(va, bytes)) return p;
    return reinterpret_cast<void*>(ngb_guest_pointer(va, bytes));
}
// A const descriptor access cannot dirty vertex or texture data. The direct
// renderer publishes these banks only for ordinary contiguous RAM. A tracked
// render target or a cross-page span still needs the runtime's access checks.
inline const void* ReadPage(uint32_t va, size_t bytes) {
    if (va < (64u << 20)) return DirectPage(va, bytes);
    uint32_t physical = va - 0x80000000u;
    unsigned offset = va & 4095u;
    if (physical < (128u << 20) && bytes && bytes <= 4096u - offset) {
        auto** bank = ngb_guest_banks[va >> 26];
        if (bank && !ngb_target_pages[physical >> 12])
            if (auto* page = bank[(va >> 12) & 0x3fffu]) return page + offset;
    }
    return nullptr;
}
inline const void* ReadPtr(uint32_t va, size_t bytes) {
    if (const void* page = ReadPage(va, bytes)) return page;
    return reinterpret_cast<void*>(ngb_guest_pointer(va, bytes));
}
#else
inline void* HostPtr(uint32_t va, size_t = 1) { return reinterpret_cast<void*>(uintptr_t(va) + uintptr_t(g_xbox_mem_offset)); }
inline const void* ReadPtr(uint32_t va, size_t bytes) { return HostPtr(va, bytes); }
#endif
inline uint32_t R32(uint32_t va) { uint32_t v; std::memcpy(&v, ReadPtr(va, 4), 4); return v; }
inline uint16_t R16(uint32_t va) { uint16_t v; std::memcpy(&v, ReadPtr(va, 2), 2); return v; }
inline uint8_t R8(uint32_t va) { return *static_cast<const uint8_t*>(ReadPtr(va, 1)); }
inline void W32(uint32_t va, uint32_t v) { std::memcpy(HostPtr(va, 4), &v, 4); }
}  // namespace kernel

namespace mem {
// a resource's physical address to where the title sees it: contiguous memory is mapped at 0x80000000
inline uint32_t VirtualFromPhysical(uint32_t pa) { return pa | 0x80000000u; }
// a resource's data: the renderer's own vertex buffer headers (Common bit 31) hold a virtual address
inline uint32_t ResourceData(uint32_t res) {
    uint32_t d = kernel::R32(res + 4);
    return (kernel::R32(res) & 0x80000000u) ? d : VirtualFromPhysical(d);
}
}  // namespace mem
