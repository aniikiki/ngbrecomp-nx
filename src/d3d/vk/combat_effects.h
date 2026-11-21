// UT additive sprites. The clip planes are in the texture's coordinate system,
// so perspective, skinning, depth and the game's draw order remain on the GPU.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>

#include "gpu/vertex.h"

namespace gpu {

struct CombatHull {
    std::array<float, 4> lo{}, hi{};
    bool useful = false;
};

// Bounds of all nonzero BC3 texels, including the complete bilinear footprint.
// BC3 interpolation can round differently across GPUs. A code is considered
// zero only when the format guarantees it from the endpoints, before rounding.
inline CombatHull CombatAlphaHull(const uint8_t* blocks, unsigned w, unsigned h) {
    CombatHull hull;
    hull.lo.fill(4.f);
    hull.hi.fill(-4.f);
    const float du = 1.f / w, dv = 1.f / h;
    const std::array<float, 4> pad{du, dv, du + dv, du + dv};
    for (unsigned y = 0; y < h; ++y) {
        for (unsigned x = 0; x < w; ++x) {
            const uint8_t* b = blocks + 16 * ((y / 4) * ((w + 3) / 4) + x / 4);
            unsigned bit = 3 * ((y % 4) * 4 + x % 4);
            unsigned bits = b[2 + bit / 8] | (unsigned(b[3 + bit / 8]) << 8);
            unsigned i = (bits >> (bit % 8)) & 7;
            if ((i == 0 && !b[0]) || (i == 1 && !b[1]) ||
                (i == 6 && b[0] <= b[1]) || (i >= 2 && i <= 5 && !b[0] && !b[1])) continue;
            // Include samples across a repeat seam, even for a clamp sampler.
            float u = (float(x) + 0.5f) * du, v = (float(y) + 0.5f) * dv;
            float u2 = x == 0 ? u + 1 : x + 1 == w ? u - 1 : u;
            float v2 = y == 0 ? v + 1 : y + 1 == h ? v - 1 : v;
            float u0 = std::min(u,u2), u1 = std::max(u,u2), v0 = std::min(v,v2), v1 = std::max(v,v2);
            std::array<float,4> lo{u0,v0,u0+v0,u0-v1}, hi{u1,v1,u1+v1,u1-v0};
            for (unsigned k = 0; k < 4; ++k) {
                hull.lo[k] = std::min(hull.lo[k], lo[k] - pad[k]);
                hull.hi[k] = std::max(hull.hi[k], hi[k] + pad[k]);
            }
        }
    }
    // The all-zero case clips the entire draw. Avoid a new pipeline for a
    // footprint which covers essentially the entire tile.
    hull.useful = hull.lo[0] > .02f || hull.lo[1] > .02f || hull.hi[0] < .98f || hull.hi[1] < .98f ||
                  hull.lo[2] > .15f || hull.hi[2] < 1.85f || hull.lo[3] > -.85f || hull.hi[3] < .85f;
    return hull;
}

inline bool CombatQuadIsInvisible(const Assembled& a) {
    const auto& e = a.elements[3];
    if (a.vertex_count != 4 || a.index_count || !(a.regs & (1u << 3)) ||
        e.format != 87 || e.buffer >= a.buffer_count) return false; // B8G8R8A8_UNORM
    const auto& b = a.buffers[e.buffer];
    if (!b.src || !b.stride || e.offset + 4u > b.stride ||
        size_t(e.offset) + 3 * size_t(b.stride) + 4 > b.bytes) return false;
    for (unsigned i=0; i<4; ++i)
        if (b.src[e.offset+i*b.stride+3]) return false;
    return true;
}

// Coordinates must stay within a single sampler tile. At an exact upper
// boundary the original sampler can see the next tile (covered above).
inline bool CombatTile(const Assembled& a, uint32_t address_u, uint32_t address_v, std::array<float,4>& tile) {
    if (!(a.regs & (1u << 9))) return false;
    const auto& e = a.elements[9];
    if (e.format != 16 || e.buffer >= a.buffer_count) return false; // R32G32_FLOAT
    const auto& b = a.buffers[e.buffer];
    if (!b.src || !b.stride || e.offset + 8u > b.stride || e.offset + 8u > b.bytes) return false;
    unsigned n = 1 + (b.bytes - e.offset - 8u) / b.stride;
    if (n > 128) return false;
    float lo[2] = {1024,1024}, hi[2] = {-1024,-1024};
    for (unsigned i = 0; i < n; ++i) {
        float uv[2];
        std::memcpy(uv, b.src + i * b.stride + e.offset, sizeof(uv));
        for (unsigned k = 0; k < 2; ++k) {
            if (!(std::abs(uv[k]) < 1024)) return false;
            lo[k] = std::min(lo[k],uv[k]); hi[k] = std::max(hi[k],uv[k]);
        }
    }
    const uint32_t address[2] = {address_u,address_v};
    for (unsigned k = 0; k < 2; ++k) {
        if (address[k] != 1 && address[k] != 3 && address[k] != 5) return false;
        tile[k] = address[k] == 1 ? std::floor(lo[k]) : 0;
        if (lo[k] < tile[k] || hi[k] > tile[k] + 1) return false;
    }
    tile[2] = tile[0] + tile[1];
    tile[3] = tile[0] - tile[1];
    return true;
}

} // namespace gpu
