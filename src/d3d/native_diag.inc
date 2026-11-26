// Included once by hle.cpp, outside its anonymous namespace. Producers only
// enqueue integer rows; the combat writer consumes them off the display thread.
#ifdef NGB_NATIVE_DIAG
#include "native_cpu_phases.h"
bool ngb_native_diag_on, ngb_native_diag_sample;
namespace {
NativeDiagScope* nd_stack[16]{};
unsigned nd_worker, nd_draws;
uint64_t nd_last, nd_frame_time, nd_frame_cpu, nd_calls[ND_COUNT]{}, nd_ns[ND_COUNT]{}, nd_words;
// Each worker remembers its running fiber's innermost CPU phase. The scheduler
// saves that phase with the fiber when it parks it, even between capture windows.
unsigned nd_cpu_phase[16]{}, nd_phase_calls[NGB_CPU_PHASE_COUNT]{};
uint64_t nd_cpu_since, nd_phase_us[NGB_CPU_PHASE_COUNT]{};

void NativeDiagCharge(uint64_t now) {
    if (ngb_native_diag_on && nd_stack[nd_worker]) {
        const unsigned kind = nd_stack[nd_worker]->kind;
        if (ngb_native_diag_sample || kind >= ND_PRESENT) nd_ns[kind] += now - nd_last;
    }
    nd_last = now;
}
uint64_t NativeDiagCpuDelta(uint64_t before, uint64_t after) {
    return before && after >= before ? after - before : 0;
}
void ChargePhaseCpu(uint64_t cpu) {
    unsigned phase = nd_cpu_phase[nd_worker];
    if (phase && ngb_native_diag_on) nd_phase_us[phase] += NativeDiagCpuDelta(nd_cpu_since, cpu);
    nd_cpu_since = cpu;
}
}

extern "C" unsigned ngb_native_cpu_resume(unsigned phase) {
    unsigned previous = nd_cpu_phase[nd_worker];
    if (phase != previous) {
        if (ngb_native_diag_on) ChargePhaseCpu(ngb_combat_cpu_us());
        nd_cpu_phase[nd_worker] = phase;
    }
    return previous;
}
extern "C" unsigned ngb_native_cpu_enter(unsigned phase) {
    if (ngb_native_diag_on) ++nd_phase_calls[phase];
    return ngb_native_cpu_resume(phase);
}
// During an opted-in boot, track switches between capture windows too so a
// later activation starts on the right guest worker's stack.
extern "C" void ngb_native_diag_switch(unsigned next, uint64_t now) {
    if (ngb_native_diag_on) {
        NativeDiagCharge(now);
        if (nd_cpu_phase[nd_worker] != nd_cpu_phase[next]) ChargePhaseCpu(ngb_combat_cpu_us());
    }
    nd_worker = next;
}
void NativeDiagScope::Enter(unsigned k) {
    ++nd_calls[k];
    // Keep the nesting across frame boundaries: a background VBlank waiter can
    // stay suspended over several presents. Only sampled frames time hot calls.
    if (!ngb_native_diag_sample && k < ND_PRESENT) return;
    NativeDiagCharge(ngb_elapsed_ns());
    kind = k;
    worker = nd_worker; previous = nd_stack[worker]; nd_stack[worker] = this; linked = true;
}
void NativeDiagScope::Leave() {
    NativeDiagCharge(ngb_elapsed_ns());
    nd_stack[worker] = previous;
}
void NativeDiagWords(unsigned words) { if (ngb_native_diag_on) nd_words += words; }
void NativeDiagFrame(unsigned frame) {
    const bool on = ngb_combat_enabled && ngb_combat_active();
    if (!on && !ngb_native_diag_on) return;
    uint64_t now = ngb_elapsed_ns();
    uint64_t cpu = ngb_combat_cpu_us();
    ChargePhaseCpu(cpu);
    if (ngb_native_diag_on) {
        NativeDiagCharge(now);
        uint64_t n[] = {frame, now/1000, cpu, (now-nd_frame_time)/1000,
            NativeDiagCpuDelta(nd_frame_cpu,cpu), ngb_native_diag_sample, nd_draws,
            nd_calls[ND_STATE], nd_calls[ND_SHADER], nd_calls[ND_RESOURCE], nd_calls[ND_DRAW],
            nd_calls[ND_HELPER], nd_calls[ND_OTHER], nd_calls[ND_INLINE], nd_words,
            nd_ns[ND_FRAME_WAIT]/1000, nd_ns[ND_FENCE_WAIT]/1000, nd_ns[ND_RESOURCE_WAIT]/1000,
            nd_ns[ND_READBACK_WAIT]/1000, nd_ns[ND_VBLANK_WAIT]/1000, nd_ns[ND_PACE]/1000,
            nd_ns[ND_PRESENT]/1000, nd_ns[ND_CALLBACK]/1000,
            nd_calls[ND_FRAME_WAIT], nd_calls[ND_RESOURCE_WAIT], nd_calls[ND_READBACK_WAIT],
            nd_phase_us[NGB_CPU_PARTICLE_UPDATE], nd_phase_us[NGB_CPU_PARTICLE_PREPARE],
            nd_phase_calls[NGB_CPU_PARTICLE_UPDATE], nd_phase_calls[NGB_CPU_PARTICLE_PREPARE],
            nd_phase_us[NGB_CPU_ORDERED_LIST], nd_phase_us[NGB_CPU_EFFECT_PREPARE], nd_phase_us[NGB_CPU_DRAW_TASK],
            nd_phase_us[NGB_CPU_PLAYER_UPDATE], nd_phase_us[NGB_CPU_SCENE_ACTORS], nd_phase_us[NGB_CPU_INTERRUPT],
            nd_phase_calls[NGB_CPU_ORDERED_LIST]};
        ngb_combat_row('N', n, sizeof n/sizeof *n);
        if (ngb_native_diag_sample) {
            uint64_t t[ND_COUNT+2] = {frame, now/1000};
            for (unsigned i=0; i<ND_COUNT; ++i) t[i+2] = nd_ns[i];
            ngb_combat_row('T', t, ND_COUNT+2);
        }
    }
    std::fill(std::begin(nd_calls), std::end(nd_calls), 0);
    std::fill(std::begin(nd_ns), std::end(nd_ns), 0);
    std::fill(std::begin(nd_phase_us), std::end(nd_phase_us), 0);
    std::fill(std::begin(nd_phase_calls), std::end(nd_phase_calls), 0);
    nd_words = nd_draws = 0;
    ngb_native_diag_on = on;
    ngb_native_diag_sample = on && (frame % 32 == 0);
    nd_frame_time = nd_last = now; nd_frame_cpu = cpu;
}
NativeDiagSwap::NativeDiagSwap(unsigned frame, unsigned interval) : on(ngb_native_diag_on) {
    if (!on) return;
    std::fill(std::begin(v), std::end(v), 0);
    v[0]=frame; v[1]=ngb_elapsed_ns()/1000; v[2]=ngb_combat_cpu_us(); v[3]=interval;
}
void NativeDiagSwap::Plan(unsigned periods,unsigned previous,unsigned current,unsigned target,bool retargeted) {
    if (!on) return;
    v[4]=periods; v[5]=previous; v[6]=current; v[7]=target; v[8]=retargeted;
}
void NativeDiagSwap::WaitBegin(uint64_t deadline) {
    if (!on) return;
    v[9]=deadline/1000; v[10]=ngb_elapsed_ns()/1000; v[12]=ngb_combat_cpu_us();
}
void NativeDiagSwap::WaitEnd() {
    if (!on) return;
    v[11]=ngb_elapsed_ns()/1000-v[10]; v[12]=NativeDiagCpuDelta(v[12],ngb_combat_cpu_us());
}
void NativeDiagSwap::PresentBegin() { if (on) v[13]=ngb_elapsed_ns()/1000; }
void NativeDiagSwap::PresentEnd() { if (on) v[14]=ngb_elapsed_ns()/1000-v[13]; }
void NativeDiagSwap::Finish(unsigned blank,unsigned draws) {
    if (!on) return;
    nd_draws = draws;
    v[15]=ngb_elapsed_ns()/1000-v[1]; v[16]=NativeDiagCpuDelta(v[2],ngb_combat_cpu_us());
    v[17]=blank; v[18]=draws;
    ngb_combat_row('V',v,sizeof v/sizeof *v);
}
#endif
