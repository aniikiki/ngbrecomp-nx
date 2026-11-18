#pragma once
#include <cstdint>

// A maximum frame rate, independent of the display's refresh phase. A late
// frame is submitted immediately; it never waits for a later vblank or catches
// up by running several short simulation frames after a stall.
struct NativeFramePacer {
    static constexpr uint64_t period = 16666667;
    uint64_t submitted = 0;
    uint64_t Deadline(uint64_t now) const {
        return submitted && now < submitted + period ? submitted + period : 0;
    }
    void Submitted(uint64_t now) { submitted = now; }
};
