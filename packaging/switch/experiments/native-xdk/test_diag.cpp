// A fake clock makes overlap and cooperative-worker attribution deterministic.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iterator>
#include <vector>
#define NGB_NATIVE_DIAG
#include "native_diag.h"
static uint64_t clock_ns = 1000000;
int ngb_combat_enabled = 1;
int ngb_combat_active() { return 1; }
uint64_t ngb_elapsed_ns() { return clock_ns; }
uint64_t ngb_combat_cpu_us() { return clock_ns/1000; }
struct Row { char kind; std::vector<uint64_t> values; };
static std::vector<Row> rows;
void ngb_combat_row(int kind,const uint64_t* values,unsigned count) {
    rows.push_back({char(kind),{values,values+count}});
}
#include "native_diag.inc"
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
    assert(n.size()==26 && n[5]==1 && n[6]==500 && n[20]==25);
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
    ngb_combat_enabled=0; NativeDiagFrame(66);
    auto before=rows.size();
    { NativeDiagScope disabled(ND_STATE); clock_ns+=100000; }
    NativeDiagFrame(67); assert(rows.size()==before);
}
