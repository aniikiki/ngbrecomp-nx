// A CPU read of an ordinary physical alias is safe to borrow directly.
// A target, protected page, retired mapping or multi-page span uses the
// runtime accessor, where synchronization and allocation checks take place.
#include "kernel/kernel.h"
#include <cassert>

extern "C" {
unsigned char* ngb_direct_pages[16384]{};
unsigned char** ngb_guest_banks[64]{};
unsigned char ngb_target_pages[32768]{};
}
static unsigned char* pages[16384]{};
static unsigned char mapped[4096], slow[8192];
static unsigned calls;

extern "C" uintptr_t ngb_guest_pointer(uint32_t, size_t) {
    ++calls;
    return reinterpret_cast<uintptr_t>(slow);
}

int main() {
    constexpr uint32_t address = 0x84003000;
    ngb_guest_banks[address >> 26] = pages;
    pages[3] = mapped;
    assert(kernel::ReadPage(address + 4096 - 12, 12) == mapped + 4096 - 12);
    assert(!kernel::ReadPage(address + 4096 - 12, 20));
    assert(kernel::ReadPtr(address + 4092, 4) == mapped + 4092 && calls == 0);
    assert(kernel::ReadPtr(address + 4092, 8) == slow && calls == 1);
    ngb_target_pages[(address - 0x80000000) >> 12] = 1;
    assert(!kernel::ReadPage(address, 24) && calls == 1);
    assert(kernel::ReadPtr(address, 16) == slow && calls == 2);
    ngb_target_pages[(address - 0x80000000) >> 12] = 0;
    pages[3] = nullptr;
    assert(!kernel::ReadPage(address, 12));
    assert(kernel::ReadPtr(address, 4) == slow && calls == 3);
    pages[3] = mapped;
    ngb_guest_banks[address >> 26] = nullptr;
    assert(kernel::ReadPtr(address, 4) == slow && calls == 4);
    ngb_direct_pages[1] = mapped;
    assert(kernel::ReadPtr(4096, 4) == mapped && calls == 4);
    assert(kernel::HostPtr(address, 4) == slow && calls == 5);
    ngb_guest_banks[address >> 26] = pages;
    const uint32_t value = 0x12345678;
    std::memcpy(mapped + 12, &value, sizeof value);
    assert(kernel::R32(address + 12) == value && kernel::R16(address + 12) == 0x5678);
    assert(kernel::R8(address + 15) == 0x12 && calls == 5);
    kernel::W32(address + 12, 0x01020304);
    assert(calls == 6 && kernel::R32(address + 12) == value);
    ngb_target_pages[(address - 0x80000000) >> 12] = 1;
    assert(kernel::R32(address + 12) == 0x01020304 && calls == 7);
    assert(kernel::R16(address + 12) == 0x0304 && kernel::R8(address + 12) == 4 && calls == 9);
}
