#pragma once
#include <algorithm>
#include <bit>
#include <cstdint>
#include <cstring>

namespace gpu {

// The inverse of texture.cpp's renderable pixel formats. GPU colour is BGRA8;
// depth and stencil are separate Vulkan aspects. Return 0 for non-target formats.
inline unsigned EncodeRenderPixel(uint32_t format, uint32_t bgra, float depth, uint8_t stencil, uint8_t* out) {
    uint32_t b = bgra & 255, g = bgra >> 8 & 255, r = bgra >> 16 & 255, a = bgra >> 24;
    uint32_t value = 0;
    unsigned bytes = 0;
    switch (format) {
    case 0x00: case 0x13: case 0x01: case 0x1b: value = b; bytes = 1; break;
    case 0x19: case 0x1f: value = a; bytes = 1; break;
    case 0x1a: case 0x20: value = b | a << 8; bytes = 2; break;
    case 0x02: case 0x10: case 0x03: case 0x1c:
        value = (b >> 3) | (g >> 3) << 5 | (r >> 3) << 10 | (a >> 7) << 15; bytes = 2; break;
    case 0x04: case 0x1d:
        value = (b >> 4) | (g >> 4) << 4 | (r >> 4) << 8 | (a >> 4) << 12; bytes = 2; break;
    case 0x05: case 0x11:
        value = (b >> 3) | (g >> 2) << 5 | (r >> 3) << 11; bytes = 2; break;
    case 0x06: case 0x12: case 0x07: case 0x1e: value = bgra; bytes = 4; break;
    case 0x16: case 0x29: value = b | r << 8; bytes = 2; break;
    case 0x17: case 0x28: value = b | g << 8; bytes = 2; break;
    case 0x32: case 0x35: value = b * 257; bytes = 2; break;
    case 0x38: case 0x3d:
        value = (a >> 7) | (b >> 3) << 1 | (g >> 3) << 6 | (r >> 3) << 11; bytes = 2; break;
    case 0x39: case 0x3e:
        value = (a >> 4) | (b >> 4) << 4 | (g >> 4) << 8 | (r >> 4) << 12; bytes = 2; break;
    case 0x3a: case 0x3f: value = r | g << 8 | b << 16 | a << 24; bytes = 4; break;
    case 0x3b: case 0x40: value = a | r << 8 | g << 16 | b << 24; bytes = 4; break;
    case 0x3c: case 0x41: value = a | b << 8 | g << 16 | r << 24; bytes = 4; break;
    case 0x2a: case 0x2e:
        value = (uint32_t(double(std::clamp(depth, 0.f, 1.f)) * 16777215.0 + .5) << 8) | stencil;
        bytes = 4; break;
    case 0x2c: case 0x30:
        value = uint32_t(double(std::clamp(depth, 0.f, 1.f)) * 65535.0 + .5); bytes = 2; break;
    case 0x2b: case 0x2f: {
        uint32_t f = std::bit_cast<uint32_t>(std::max(depth, 0.f));
        value = ((f >> 23 & 255) << 24) | ((f >> 7 & 65535) << 8) | stencil; bytes = 4; break;
    }
    case 0x2d: case 0x31: {
        uint32_t f = std::bit_cast<uint32_t>(std::clamp(depth, 0.f, 1.f) * 511.9375f);
        uint32_t e = f >> 23 & 255;
        value = e < 120 ? 0 : (std::min(e - 120, 15u) << 12) | (f >> 11 & 4095);
        bytes = 2; break;
    }
    default: return 0;
    }
    std::memcpy(out, &value, bytes);
    return bytes;
}

inline uint32_t RenderPixelOffset(uint32_t x, uint32_t y, uint32_t w, uint32_t h,
                                  uint32_t bytes, uint32_t pitch, bool linear) {
    if (linear) return y * pitch + x * bytes;
    uint32_t value = 0, dest = 1;
    for (uint32_t bit = 1; bit < w || bit < h; bit <<= 1) {
        if (bit < w) { if (x & bit) value |= dest; dest <<= 1; }
        if (bit < h) { if (y & bit) value |= dest; dest <<= 1; }
    }
    return value * bytes;
}

}  // namespace gpu
