#pragma once
#include "gpu/texture.h"
#include <cstddef>
#include <cstring>

namespace gpu {
// Exact BGRA bytes; X8, swizzled, volume and generated mips need the decoder.
inline bool DirectLinearBGRA(const TextureDesc& d) {
    return d.format == 0x12 && d.linear && !d.cube && d.levels == 1 && d.depth == 1 &&
           d.width && d.height && d.pitch >= size_t(d.width) * 4;
}
inline void StageLinearBGRA(const TextureDesc& d, const uint8_t* src, uint8_t* dst) {
    const size_t row = size_t(d.width) * 4;
    if (row == d.pitch) {
        std::memcpy(dst, src, row * d.height);
    } else {
        for (size_t y = 0; y < d.height; ++y)
            std::memcpy(dst + y * row, src + y * d.pitch, row);
    }
}
}
