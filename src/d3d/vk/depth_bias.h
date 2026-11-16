#pragma once
#include <algorithm>
namespace gpu {
inline float ScaledSlopeBias(float game, float target_scale, bool depth_write, float overlay_margin) {
    return game * std::max(target_scale, 1.f) * (depth_write ? 1.f : overlay_margin);
}
}
