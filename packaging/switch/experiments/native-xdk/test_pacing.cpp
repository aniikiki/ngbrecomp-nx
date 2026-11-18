#include <cassert>
#include <cstdint>
#include <initializer_list>
#include "native_pacing.h"

int main() {
    // Simulate sustained workloads, a loading hitch, and a return to light
    // frames. Late submissions must not quantize to 30/20 fps or catch up fast.
    for (uint64_t work : {8000000ull, 16000000ull, 19000000ull, 27000000ull, 40000000ull}) {
        NativeFramePacer pacer;
        uint64_t now=1000000000;
        pacer.Submitted(now);
        for (unsigned i=0;i<120;++i) {
            uint64_t before=now; now+=work;
            if (uint64_t deadline=pacer.Deadline(now)) now=deadline;
            assert(now-before==(work<NativeFramePacer::period?NativeFramePacer::period:work));
            pacer.Submitted(now);
        }
        now+=300000000;
        assert(!pacer.Deadline(now));
        pacer.Submitted(now);
        assert(pacer.Deadline(now+1000000)==now+NativeFramePacer::period);
    }
    NativeFramePacer fresh;
    assert(!fresh.Deadline(1000000000));
}
