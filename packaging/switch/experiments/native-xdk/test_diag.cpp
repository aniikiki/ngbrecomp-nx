// A fake clock makes overlap and cooperative-worker attribution deterministic.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iterator>
#include <vector>
#define NGB_NATIVE_DIAG
#include "native_diag.h"
static uint64_t clock_ns = 1000000;
static unsigned wall_reads, cpu_reads;
int ngb_combat_enabled = 1;
static int active_window = 1;
int ngb_combat_active() { return active_window; }
uint64_t ngb_elapsed_ns() { ++wall_reads; return clock_ns; }
uint64_t ngb_combat_cpu_us() { ++cpu_reads; return clock_ns/1000; }
struct Row { char kind; std::vector<uint64_t> values; };
static std::vector<Row> rows;
void ngb_combat_row(int kind,const uint64_t* values,unsigned count) {
    rows.push_back({char(kind),{values,values+count}});
}
#include "native_diag.inc"
#ifdef TEST_PARTICLE_GATE
extern "C" void __wrap_ngb_reg_sub_00123D20();
extern "C" void __wrap_ngb_reg_sub_00123D50();
extern "C" void __wrap_ngb_reg_sub_00308CE0();
static unsigned pool_calls;
extern "C" void __real_ngb_reg_sub_00123D20() { ++pool_calls; clock_ns+=9000; }
extern "C" void __real_ngb_reg_sub_00123D50() { ++pool_calls; clock_ns+=17000; }
extern "C" void __real_ngb_reg_sub_00308CE0() { ++pool_calls; clock_ns+=13000; }
#endif
static const std::vector<uint64_t>& last(char kind) {
    for(auto i=rows.rbegin();i!=rows.rend();++i) if(i->kind==kind)return i->values;
    assert(false); return rows.front().values;
}
int main() {
    NativeDiagFrame(32);
    {
        NativeDiagScope state(ND_STATE); clock_ns+=10000;
        { NativeDiagScope deferred(ND_DEFERRED); clock_ns+=20000; }
        clock_ns+=5000;
        {
            NativeDiagScope pace(ND_PACE); clock_ns+=10000;
            ngb_native_diag_switch(1,clock_ns); clock_ns+=40000;
            { NativeDiagScope helper(ND_HELPER); clock_ns+=20000; }
            ngb_native_diag_switch(0,clock_ns); clock_ns+=15000;
        }
        clock_ns+=5000;
    }
    NativeDiagSwap swap(33,1); swap.Plan(1,10,11,12,true);
    swap.WaitBegin(clock_ns+16000000); clock_ns+=16000000; swap.WaitEnd();
    swap.PresentBegin(); clock_ns+=5000; swap.PresentEnd(); swap.Finish(12,500);
    NativeDiagFrame(33);
    const auto& t=last('T');
    assert(t.size()==20 && t[ND_STATE+2]==20000 && t[ND_DEFERRED+2]==20000);
    assert(t[ND_PACE+2]==25000 && t[ND_HELPER+2]==20000);
    const auto& n=last('N');
    assert(n.size()==37 && n[5]==1 && n[6]==500 && n[20]==25);
    const auto& v=last('V');
    assert(v.size()==19 && v[8]==1 && v[11]==16000 && v[14]==5);
    assert(v[9]-v[10]==16000 && v[17]-v[5]==2);
    // A suspended background VBlank call spans the frame boundary. Work by
    // worker zero must not be attributed to it, in either sampling mode.
    ngb_native_diag_switch(1,clock_ns);
    {
        NativeDiagScope blank(ND_VBLANK_WAIT); clock_ns+=100000;
        ngb_native_diag_switch(0,clock_ns); NativeDiagFrame(64);
        assert(last('N')[19]==100);
        clock_ns+=200000;
        ngb_native_diag_switch(1,clock_ns); clock_ns+=30000;
    }
    ngb_native_diag_switch(0,clock_ns); NativeDiagFrame(65);
    assert(last('T')[ND_VBLANK_WAIT+2]==30000);
    auto update = ngb_native_cpu_enter(NGB_CPU_PARTICLE_UPDATE); clock_ns+=10000;
    auto prepare = ngb_native_cpu_enter(NGB_CPU_PARTICLE_PREPARE); clock_ns+=7000;
    ngb_native_diag_switch(1,clock_ns); clock_ns+=80000;
    ngb_native_diag_switch(0,clock_ns); clock_ns+=3000;
    ngb_native_cpu_resume(prepare); clock_ns+=5000;
    NativeDiagFrame(66);
    assert(last('N')[26]==15 && last('N')[27]==10 && last('N')[28]==1 && last('N')[29]==1);
    clock_ns+=6000; ngb_native_cpu_resume(update); NativeDiagFrame(67);
    assert(last('N')[26]==6 && !last('N')[27] && !last('N')[28] && !last('N')[29]);
#ifdef TEST_PARTICLE_GATE
    __wrap_ngb_reg_sub_00123D20(); __wrap_ngb_reg_sub_00123D50(); __wrap_ngb_reg_sub_00308CE0(); NativeDiagFrame(68);
    assert(last('N')[26]==9 && last('N')[27]==17 && last('N')[28]==1 && last('N')[29]==1);
    assert(last('N')[30]==13 && last('N')[36]==1);
#endif
    // Switch away in a nested list dispatch. An actor task, another worker and
    // an interrupt execute before the drawing fiber resumes in the next frame.
    ngb_native_cpu_resume(NGB_CPU_DRAW_TASK); clock_ns+=2000;
    unsigned draw = ngb_native_cpu_enter(NGB_CPU_ORDERED_LIST); clock_ns+=4000;
    unsigned fiber = ngb_native_cpu_resume(NGB_CPU_PLAYER_UPDATE); clock_ns+=7000;
    ngb_native_diag_switch(1,clock_ns);
    ngb_native_cpu_resume(NGB_CPU_SCENE_ACTORS); clock_ns+=5000;
    unsigned actor = ngb_native_cpu_resume(NGB_CPU_INTERRUPT); clock_ns+=3000;
    ngb_native_cpu_resume(actor); ngb_native_diag_switch(0,clock_ns);
    NativeDiagFrame(69);
    const auto& split=last('N');
    assert(split[4]==21 && split[30]==4 && split[32]==2 && split[33]==7 && split[34]==5 && split[35]==3);
    ngb_native_cpu_resume(fiber); clock_ns+=11000;
    ngb_native_cpu_resume(draw); clock_ns+=1000;
    ngb_native_cpu_resume(NGB_CPU_EFFECT_PREPARE); clock_ns+=6000;
    update=ngb_native_cpu_enter(NGB_CPU_PARTICLE_UPDATE); clock_ns+=4000;
    ngb_native_cpu_resume(update); NativeDiagFrame(70);
    assert(last('N')[4]==22 && last('N')[26]==4 && last('N')[30]==11 && last('N')[31]==6 && last('N')[32]==1);
    assert(last('N')[36]==0); // Dispatch started in the preceding frame.
    active_window=0; NativeDiagFrame(71);
    auto inactive_reads=cpu_reads;
    unsigned parent=ngb_native_cpu_enter(NGB_CPU_ORDERED_LIST);
    clock_ns+=300000; assert(cpu_reads==inactive_reads);
    active_window=1; NativeDiagFrame(72);
    clock_ns+=8000; ngb_native_cpu_resume(parent);
    clock_ns+=2000; NativeDiagFrame(73);
    assert(last('N')[4]==10 && last('N')[30]==8 && last('N')[31]==2 && last('N')[36]==0);
    ngb_combat_enabled=0; NativeDiagFrame(74);
    auto before=rows.size();
    auto wall_before=wall_reads, cpu_before=cpu_reads;
#ifdef TEST_PARTICLE_GATE
    __wrap_ngb_reg_sub_00123D20(); __wrap_ngb_reg_sub_00123D50(); __wrap_ngb_reg_sub_00308CE0(); assert(pool_calls==6);
#endif
    { NativeDiagScope disabled(ND_STATE); clock_ns+=100000; }
    NativeDiagSwap quiet(67,1); quiet.Plan(1,10,11,12,true);
    quiet.WaitBegin(clock_ns); quiet.WaitEnd();
    quiet.PresentBegin(); quiet.PresentEnd(); quiet.Finish(12,500);
    NativeDiagFrame(67); assert(rows.size()==before);
    assert(wall_reads==wall_before && cpu_reads==cpu_before);
}
