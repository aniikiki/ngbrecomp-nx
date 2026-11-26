#pragma once
#include <cstdint>

namespace gpu {
enum class CombatEffect : uint8_t { None, HistoryCapture, HistoryComposite, Transparent };
// Indices match the recorder's fixed StateRanges; assertions at that boundary
// protect this contract. A missing revision always requires a full comparison.
struct PreparedState {
    uint64_t revision;
    uint32_t changed;
    static constexpr uint32_t Simple = 1u << 1;
    static constexpr uint32_t DepthClip = 1u << 4;
    static constexpr uint32_t PixelCombiners = (1u << 0) | (1u << 2) | (1u << 3) | (1u << 5);
    static constexpr uint32_t SimpleMethod(uint32_t method) {
        method &= 0x1ffcu;
        if (method == 0x1d78) return DepthClip;
        return (method & 0x1f00) == 0x300 ? Simple : PixelCombiners;
    }
    static constexpr uint32_t RenderStates = 1u << 6;
    static constexpr uint32_t Vertex = 1u << 7;
    static constexpr uint32_t PixelConstantsAndTargets = 1u << 8;
    static constexpr uint32_t ViewMatrices = 1u << 9;
    static constexpr uint32_t TextureMatrices = 1u << 10;
    static constexpr uint32_t WorldMatrices = 1u << 11;
    static constexpr uint32_t Material = 1u << 12;
    static constexpr uint32_t LightsAndOffset = 1u << 13;
    static constexpr uint32_t DepthScale = 1u << 14;
    static constexpr uint32_t TextureStage(unsigned stage) { return (1u << 15) << stage; }
    static constexpr uint32_t TexturesAndPalettes = 1u << 19;
    static constexpr uint32_t Streams = 1u << 20;
    // A native binding can touch the old and new header and a surface's parent.
    // Collisions only cause another live check. Untracked guest writes invalidate all.
    static constexpr uint32_t HeaderWrite(uint32_t address) {
        return address ? 1u << (21 + (((address >> 4) ^ (address >> 11)) & 7)) : 0;
    }
    // Only world matrix zero and/or the per-instance texture factor changed.
    static constexpr uint32_t InstanceValues = 1u << 29;
    static constexpr uint32_t HeaderBindings = 1u << 30;
    static constexpr uint32_t ResourceHeaders = 1u << 31;
};
}
