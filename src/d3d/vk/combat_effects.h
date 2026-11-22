// Conservative bounds of filtered particle textures, for UT clip planes and
// screen scissors on the game's alpha-blended billboards.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <vulkan/vulkan_core.h>

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
    if (!w || !h) return hull;
    auto transparent = [&](unsigned x, unsigned y) {
        const uint8_t* b = blocks + 16 * ((y / 4) * ((w + 3) / 4) + x / 4);
        unsigned bit = 3 * ((y % 4) * 4 + x % 4);
        unsigned bits = b[2 + bit / 8] | (unsigned(b[3 + bit / 8]) << 8);
        unsigned i = (bits >> (bit % 8)) & 7;
        return (i == 0 && !b[0]) || (i == 1 && !b[1]) ||
               (i == 6 && b[0] <= b[1]) || (i >= 2 && i <= 5 && !b[0] && !b[1]);
    };
    // Four occupied corners already span every axis. Most solid textures
    // need only four texel inspections at upload.
    if (!transparent(0,0) && !transparent(w-1,0) && !transparent(0,h-1) && !transparent(w-1,h-1)) return hull;
    hull.lo.fill(4.f);
    hull.hi.fill(-4.f);
    const float du = 1.f / w, dv = 1.f / h;
    const std::array<float, 4> pad{du, dv, du + dv, du + dv};
    for (unsigned y = 0; y < h; ++y) {
        for (unsigned x = 0; x < w; ++x) {
            if (transparent(x,y)) continue;
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

// Both colour and alpha modulate their argument with CURRENT and feed the next stage.
inline bool ModulatesCurrent(const std::array<uint32_t,kTssCount>& stage, uint32_t arg) {
    return stage[kTssColorOp] == 4 && stage[kTssColorArg1] == arg && stage[kTssColorArg2] == 1 &&
           stage[kTssAlphaOp] == 4 && stage[kTssAlphaArg1] == arg && stage[kTssAlphaArg2] == 1 &&
           stage[kTssResultArg] != 5;
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

constexpr unsigned kParticleWindowCount = 8;
using ParticleWindows = std::array<VkRect2D, kParticleWindowCount>;

// Bound the nonzero part of a textured strip in screen space. A scissor
// leaves the original triangles, interpolation and texture derivatives intact.
inline void ParticleScissor(const Assembled& a, const CombatHull& hull, const std::array<float,4>& tile,
                            const float* wvp, unsigned width, unsigned height, VkRect2D& sc, ParticleWindows* windows) {
    if (windows) windows->fill(sc);
    const auto& pos = a.elements[0];
    const auto& tex = a.elements[9];
    if (a.vertex_count != 4 || pos.format != 6 || tex.format != 16 ||
        pos.buffer >= a.buffer_count || tex.buffer >= a.buffer_count) return;
    const auto& pb = a.buffers[pos.buffer];
    const auto& tb = a.buffers[tex.buffer];
    if (!pb.src || !tb.src || pos.offset + 12u > pb.stride || tex.offset + 8u > tb.stride ||
        pos.offset + 3 * size_t(pb.stride) + 12 > pb.bytes || tex.offset + 3 * size_t(tb.stride) + 8 > tb.bytes) return;

    double corner[4][5], error[5]{};
    unsigned seen = 0;
    for (unsigned i = 0; i < 4; ++i) {
        float p[3], uv[2];
        std::memcpy(p, pb.src + pos.offset + i * pb.stride, sizeof(p));
        std::memcpy(uv, tb.src + tex.offset + i * tb.stride, sizeof(uv));
        float u = uv[0] - tile[0], v = uv[1] - tile[1];
        if ((u != 0 && u != 1) || (v != 0 && v != 1)) return;
        unsigned index = unsigned(u) + 2 * unsigned(v);
        seen |= 1u << index;
        for (unsigned j = 0; j < 3; ++j) {
            const float* row = wvp + (j == 2 ? 12 : 4 * j); // clip x, y, w
            double x = double(p[0])*row[0], y = double(p[1])*row[1], z = double(p[2])*row[2];
            double value = x + y + z + row[3];
            if (!std::isfinite(value)) return;
            corner[index][j] = value;
            error[j] = std::max(error[j], (std::abs(x)+std::abs(y)+std::abs(z)+std::abs(row[3])) * 4e-6);
        }
    }
    if (seen != 15) return;
    if (windows) {
        // Numerators of screen X+Y and X-Y, before adding the viewport origin.
        for (auto& c : corner) {
            c[3] = (width*c[0] - height*c[1])*0.5;
            c[4] = (width*c[0] + height*c[1])*0.5;
        }
        error[3] = error[4] = (width*error[0] + height*error[1])*0.5;
    }
    double lo[5], hi[5];
    for (unsigned j = 0; j < (windows ? 5u : 3u); ++j) {
        // In either triangle the homogeneous coordinate is p00 + u*A + v*B
        // plus the barycentric weight of p11 times its departure from a plane.
        double origin = corner[0][j], du = corner[1][j]-origin, dv = corner[2][j]-origin;
        double warp = corner[3][j]-origin-du-dv;
        auto range = [&](double u, double v, unsigned axis) {
            double a0 = u*hull.lo[axis], a1 = u*hull.hi[axis];
            double b0 = v*hull.lo[axis+1], b1 = v*hull.hi[axis+1];
            return std::array<double,2>{std::min(a0,a1)+std::min(b0,b1), std::max(a0,a1)+std::max(b0,b1)};
        };
        auto uv = range(du,dv,0), diagonals = range((du+dv)*0.5,(du-dv)*0.5,2);
        lo[j] = origin + std::max(uv[0],diagonals[0]) + std::min(0.0,warp) - error[j];
        hi[j] = origin + std::min(uv[1],diagonals[1]) + std::max(0.0,warp) + error[j];
        if (lo[j] > hi[j]) return;
    }
    if (lo[2] <= 0) return;
    auto lower = [&](int j) { return std::min(lo[j]/lo[2],lo[j]/hi[2]); };
    auto upper = [&](int j) { return std::max(hi[j]/lo[2],hi[j]/hi[2]); };
    // Negative Vulkan viewport height. Round outwards and leave two physical
    // pixels for rasterizer subpixel precision at a primitive edge.
    int x0 = std::max(sc.offset.x, int(std::floor((1+std::clamp(lower(0),-1.0,1.0))*width*0.5))-2);
    int x1 = std::min(sc.offset.x+int(sc.extent.width), int(std::ceil((1+std::clamp(upper(0),-1.0,1.0))*width*0.5))+2);
    int y0 = std::max(sc.offset.y, int(std::floor((1-std::clamp(upper(1),-1.0,1.0))*height*0.5))-2);
    int y1 = std::min(sc.offset.y+int(sc.extent.height), int(std::ceil((1-std::clamp(lower(1),-1.0,1.0))*height*0.5))+2);
    x1 = std::max(x0,x1);
    y1 = std::max(y0,y1);
    sc = {{x0,y0}, {unsigned(x1-x0),unsigned(y1-y0)}};
    if (!windows) return;
    // Intersect each horizontal band with the two screen diagonals. The union
    // still contains the entire filtered footprint and takes one hardware draw.
    double sum = (double(width)+height)*0.5, diff = (double(width)-height)*0.5;
    for (unsigned i = 0; i < windows->size(); ++i) {
        int top = y0 + int(sc.extent.height*i/kParticleWindowCount);
        int bottom = y0 + int(sc.extent.height*(i+1)/kParticleWindowCount);
        double left = std::max(sum+lower(3)-bottom, diff+lower(4)+top)-4;
        double right = std::min(sum+upper(3)-top, diff+upper(4)+bottom)+4;
        int l = int(std::floor(std::clamp(left,double(x0),double(x1))));
        int r = int(std::ceil(std::clamp(right,double(l),double(x1))));
        (*windows)[i] = {{l,top}, {unsigned(r-l),unsigned(bottom-top)}};
    }
}

} // namespace gpu
