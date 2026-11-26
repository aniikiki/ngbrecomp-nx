#pragma once
#include <cstdint>

// Guest-thread scopes. Timings are exclusive scheduled wall time, not CPU time.
// The cooperative scheduler pauses a scope while another guest worker runs.
enum NativeDiagKind {
    ND_STATE, ND_SHADER, ND_RESOURCE, ND_DRAW, ND_HELPER, ND_OTHER,
    ND_INLINE, ND_DEFERRED, ND_RECORD, ND_POLL,
    ND_PRESENT, ND_CALLBACK, ND_FRAME_WAIT, ND_FENCE_WAIT, ND_RESOURCE_WAIT,
    ND_READBACK_WAIT, ND_VBLANK_WAIT, ND_PACE, ND_COUNT
};

#ifdef NGB_NATIVE_DIAG
extern "C" bool ngb_native_diag_on;
extern bool ngb_native_diag_sample;
struct NativeDiagScope {
    NativeDiagScope* previous;
    unsigned kind, worker;
    bool linked = false;
    explicit NativeDiagScope(unsigned k) { if (ngb_native_diag_on) Enter(k); }
    ~NativeDiagScope() { if (linked) Leave(); }
    NativeDiagScope(const NativeDiagScope&) = delete;
    NativeDiagScope& operator=(const NativeDiagScope&) = delete;
private:
    void Enter(unsigned k);
    void Leave();
};
void NativeDiagFrame(unsigned frame);
void NativeDiagWords(unsigned words);
struct NativeDiagSwap {
    uint64_t v[19];
    bool on;
    NativeDiagSwap(unsigned frame, unsigned interval);
    void Plan(unsigned periods, unsigned previous, unsigned current, unsigned target, bool retargeted);
    void WaitBegin(uint64_t deadline);
    void WaitEnd();
    void PresentBegin();
    void PresentEnd();
    void Finish(unsigned blank, unsigned draws);
};
#else
struct NativeDiagScope { explicit NativeDiagScope(unsigned) {} };
inline void NativeDiagFrame(unsigned) {}
inline void NativeDiagWords(unsigned) {}
struct NativeDiagSwap {
    NativeDiagSwap(unsigned, unsigned) {}
    void Plan(unsigned, unsigned, unsigned, unsigned, bool) {}
    void WaitBegin(uint64_t) {}
    void WaitEnd() {}
    void PresentBegin() {}
    void PresentEnd() {}
    void Finish(unsigned, unsigned) {}
};
#endif
