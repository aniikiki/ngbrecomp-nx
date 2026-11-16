#pragma once
#include <cstdint>
#include <cstring>

namespace gpu {
// A title can set any register inline. Compare contiguous ordinary registers
// first; inspect individual blocks only in ranges that actually changed.
template<unsigned First, unsigned Count, unsigned Block>
inline uint32_t SyncConstantRange(uint8_t* dst, const uint8_t* src) {
    if (!std::memcmp(dst + First * Block, src + First * Block, Count * Block))
        return 0;
    uint32_t changes = 0;
    for (unsigned i = First; i < First + Count; ++i) {
        if (Count == 1 || std::memcmp(dst + i * Block, src + i * Block, Block)) {
            std::memcpy(dst + i * Block, src + i * Block, Block);
            changes |= 1u << i;
        }
    }
    return changes;
}
}
