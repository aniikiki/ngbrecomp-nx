// The retained nxvk object calls these libnx entry points inside image
// acquisition. Attribute only the UI's current call, including retries.
struct AcquireWait {
    uint64_t ns{};
    unsigned calls{};
};
struct AcquireTrace {
    AcquireWait dequeue, release_event, release_fence;
};
static thread_local AcquireTrace* active_acquire;

template<class Fn, class... Args>
static Result measure_acquire(AcquireWait AcquireTrace::*field, Fn fn, Args... args) {
    auto* trace = active_acquire;
    if (!trace) return fn(args...);
    // A fence wait can itself wait on an event. Charge that time only once.
    active_acquire = nullptr;
    const auto start = ngb_elapsed_ns();
    Result rc = fn(args...);
    auto& wait = trace->*field;
    wait.ns += ngb_elapsed_ns() - start;
    ++wait.calls;
    active_acquire = trace;
    return rc;
}

extern "C" {
Result __real_bqDequeueBuffer(Binder*, bool, u32, u32, u32, u32, s32*, NvMultiFence*);
Result __wrap_bqDequeueBuffer(Binder* b, bool async, u32 w, u32 h, u32 format, u32 usage,
                              s32* slot, NvMultiFence* fence) {
    return measure_acquire(&AcquireTrace::dequeue, __real_bqDequeueBuffer, b, async, w, h, format, usage, slot, fence);
}
Result __real_eventWait(Event*, u64);
Result __wrap_eventWait(Event* event, u64 timeout) {
    return measure_acquire(&AcquireTrace::release_event, __real_eventWait, event, timeout);
}
Result __real_nvMultiFenceWait(NvMultiFence*, s32);
Result __wrap_nvMultiFenceWait(NvMultiFence* fence, s32 timeout) {
    return measure_acquire(&AcquireTrace::release_fence, __real_nvMultiFenceWait, fence, timeout);
}
}
