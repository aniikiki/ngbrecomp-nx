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
    static constexpr uint32_t Bindings = 1u << 6; // rs, tss, textures, palettes, streams
    static constexpr uint32_t Vertex = 1u << 7;
    static constexpr uint32_t TextureMatrices = 1u << 10;
    static constexpr uint32_t WorldMatrices = 1u << 11;
    static constexpr uint32_t Material = 1u << 12;
    // Outside StateRanges: resources are stable only inside the owning model.
    static constexpr uint32_t ResourceHeaders = 1u << 31;
};
}
