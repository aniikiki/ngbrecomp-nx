// Compare the producer with the generated functions using the same mutable
// tree. Record the actual stack at the draw and the complete post-call state.
#define MEM16(a) (*static_cast<uint16_t*>(HostPtr(a, 2)))
#define SMEM16(a) int16_t(MEM16(a))
#define ZX16(a) uint32_t(uint16_t(a))
#define ICALL_TRACE_SIZE 16
static uint32_t g_icall_trace[ICALL_TRACE_SIZE], g_icall_trace_idx, g_icall_count;
#define RECOMP_ICALL_IS_CODE(t) ((t) != 0)
#define RECOMP_ICALL_OBSERVE_SITE(s,t) ((void)0)
#define RECOMP_ICALL_OBSERVE(t,r) ((void)0)
static std::vector<uint32_t> ordered_trace;
static constexpr uint32_t tree = 0x1201800, args = 0x1201100, top = 0x3001000;
static unsigned line_hits;
static void ngb_stop(const char*, uint32_t) { std::abort(); }
static void capture_ordered(uint32_t event) {
    ordered_trace.insert(ordered_trace.end(), {event, eax, ecx, edx, ebx, esi, edi, esp});
    for (unsigned a = esp; a <= top + 4; a += 4) ordered_trace.push_back(MEM32(a));
    for (float f : xmm0.f) {
        uint32_t bits; std::memcpy(&bits, &f, 4); ordered_trace.push_back(bits);
    }
}
void sub_00308D50(); void sub_00318410(); void sub_001CB260(); void sub_001CB510();
void sub_00308130() {
    if (model_depth) std::abort();
    capture_ordered(0x308130);
    MEM32(0x977940) ^= MEM32(esp + 4);
    ecx = edx = eax = 0x1234;
    esp += 4;
}
void sub_0030B020() {
    if (model_depth) std::abort();
    capture_ordered(0x30b020);
    MEM32(esi + 0x24) = 0x3f000000;
    esp += 4;
}
void sub_003C98C0() { capture_ordered(0x3c98c0); esp += 20; }
void ngb_d3d_prepared_line(uint32_t regs[8]) {
    ++line_hits;
    if (!model_depth || regs[0]!=eax || regs[1]!=ecx || regs[2]!=edx || regs[3]!=ebx ||
        regs[4]!=esp || regs[5]!=g_ebp || regs[6]!=esi || regs[7]!=edi) std::abort();
    sub_003C98C0(); regs[4]=esp;
}
void sub_003C56A0() { capture_ordered(0x3c56a0); Complex(150); }
void sub_003C5B10() { Complex(139); }
// The fixtures never exhaust the inline FIFO.
void sub_003CAB80() { std::abort(); } void sub_003C67B0() { std::abort(); }
void sub_003C8F10() { std::abort(); } void sub_003C6300() { std::abort(); }
void sub_003C6100() { std::abort(); }
static void ordered_icall(uint32_t t, uint32_t before, uint32_t) {
    g_icall_trace[g_icall_trace_idx++ % ICALL_TRACE_SIZE]=t; ++g_icall_count;
    if (t==0x318410) sub_00318410();
    else if (t==0x1cb260) sub_001CB260();
    else if (t==0x1cb510) sub_001CB510();
    else if (!t) { esp=before; eax=0; }
    else {
        if (model_depth) std::abort();
        capture_ordered(t);
        MEM32(tree+16)=tree+80; // The pending sibling must be read after this callback.
        MEM32(0x977944)=MEM32(args+4);
        esp+=4;
    }
}
#undef RECOMP_ICALL_SAFE_AT
#define RECOMP_ICALL_SAFE_AT(t,b,s) ordered_icall(t,b,s)
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) (++ngb_guest_polls)
#define ngb_guest_block_poll() (++ngb_guest_polls)
#include "reference_render_list.inc"
#undef ngb_guest_block_poll
static int ordered_hook(int fn) {
    if (fn != D3DF_D3DDevice_SetRenderState_LineWidth) std::abort();
    sub_003C56A0();
    return 1;
}
#define d3d_hook ordered_hook
#include "../../runtime/direct/native_render_list.inc"
#undef d3d_hook
#undef RECOMP_ENTRY
#define RECOMP_ENTRY(va) ((void)0)

static void test_render_list() {
    for (unsigned test=0; test<256; ++test) {
        std::vector<uint32_t> expected;
        for (bool native : {false,true}) {
            for (auto r:ranges) std::memset(HostPtr(r.start,r.size),0,r.size);
            std::memset(HostPtr(top-384,392),0,392);
            MEM32(kDevicePtr)=kNativeDevice; MEMF(0x4148c8)=1;
            MEM32(0x9776c8)=0x42; MEM32(0x9778fc)=0x1b02;
            MEM32(0x977bd4)=MEM32(0x977bd8)=MEM32(0x977bdc)=0x950140;
            MEM32(0x9779a8)=MEM32(0x9779b8)=2;
            MEM32(0x977a28)=MEM32(0x977a38)=1;
            MEM32(0x97790c)=test&1; MEMF(0x977944)=test&2?1.5f:1.f;
            for (unsigned i=0;i<5;++i) {
                uint32_t node=tree+20*i, arg=args+64*i;
                MEM32(node)=arg; MEM32(node+4)=0x318410;
                MEM32(arg)=0x1240000+i*64; MEMF(arg+4)=test&32?2.5f:MEMF(0x977944);
                MEM32(arg+8)=test&1; MEM16(arg+14)=1+(test%9); MEM16(arg+18)=test%3;
                MEM16(arg+12)=(test>>6)%3; MEM16(arg+16)=MEM16(arg+14)*(test%4);
            }
            MEM32(tree+12)=tree+20; MEM32(tree+16)=tree+60;
            MEM32(tree+20+16)=tree+40;
            MEM32(tree+4)=0x123456;
            if (test&4) { MEM32(tree+40+4)=0x1cb260; MEM32(args+128)=0x950140;
                MEM32(args+128+8)=0x1201400; MEM32(args+128+16)=0x3f800000; }
            if (test&8) { MEM32(tree+80+4)=0; }
            if (test&16) {
                uint32_t arg = args + 128;
                MEM32(tree+40+4) = 0x1cb510;
                MEM32(arg+0x14) = 0x1201400; MEM32(arg+0x18) = 0;
                MEM32(arg+0x1c) = 0x950140; MEM32(arg+0x24) = 0x3f800000;
                MEM32(arg+0x3c) = test & 4;
            }
            uint32_t mode=0x44b788+12*(test%3);
            MEM32(mode)=MEM32(0x9777bc)=1;
            MEM32(mode+4)=MEM32(0x9777c8)=0x302;
            MEM32(mode+8)=MEM32(0x9777cc)=1;
            if (test&16) MEM32(0x9779a8)=3; // First line has ordinary state changes.
            ngb_pending_dpcs=0; ngb_poll_mask=63; ngb_guest_polls=test%64;
            g_df=0; model_depth=0; g_icall_count=g_icall_trace_idx=0;
            std::fill(std::begin(g_icall_trace),std::end(g_icall_trace),0);
            eax=ecx=edx=0; ebx=11; esi=22; edi=33; g_ebp=44; g_seh_ebp=55;
            xmm0={{6,7,8,9}}; esp=top; MEM32(esp+4)=tree;
            ordered_trace.clear();
            if (native) { if (!ngb_direct_render_list()) std::abort(); }
            else sub_00308D50();
            capture_ordered(0); for (unsigned i=0;i<96;++i) ordered_trace.push_back(MEM32(top-380+i*4));
            ordered_trace.insert(ordered_trace.end(),std::begin(g_icall_trace),std::end(g_icall_trace));
            ordered_trace.push_back(g_icall_count);
            if (model_depth || (!(test&8) && esp!=top+4)) { std::fprintf(stderr,"bad tree return %u %d %x %d\n",test,native,esp,model_depth); std::abort(); }
            if (!native) expected=ordered_trace;
            else if (expected!=ordered_trace) {
                std::fprintf(stderr,"ordered render list case %u differs at word %zu\n",test,
                    size_t(std::mismatch(expected.begin(),expected.end(),ordered_trace.begin(),ordered_trace.end()).first-expected.begin()));
                std::abort();
            }
        }
    }
    if (line_hits<100) std::abort();
    std::printf("PASS: 256 mutable render lists and %u prepared line calls, including stack, order and draw inputs\n",line_hits);
}


// Empty command slots may combine poll tickets only while no interrupt or
// worker is due. Let a due poll change the remaining mesh count mid-model.
static void test_model_polls() {
    constexpr uint32_t model = 0x1201800, material = 0x1201400;
    for (unsigned start=0; start<64; ++start) {
        for (unsigned pending : {0u,1u}) {
            std::vector<uint32_t> expected;
            for (bool native : {false,true}) {
                ngb_guest_polls=start; ngb_poll_mask=7; ngb_pending_dpcs=pending;
                MEM32(0xd21e48)=0; MEM32(0x977bd4)=0x950140;
                MEM32(model+8)=3;
                for (unsigned i=0;i<3;++i) MEM32(model+0x94+i*32)=material;
                std::memset(HostPtr(top-256,280),0,280);
                esp=top; MEM32(esp+4)=model;
                eax=0x950140; ebx=11; esi=22; edi=33; g_df=0;
                ordered_trace.clear();
                observe_poll=[](uint64_t ticket) {
                    ordered_trace.push_back(uint32_t(ticket));
                    ordered_trace.push_back(MEM32(model+8));
                    MEM32(model+8)=2;
                };
                if (native) ngb_direct_model(); else sub_003078B0();
                observe_poll=nullptr;
                ordered_trace.push_back(uint32_t(ngb_guest_polls));
                if (!native) expected=ordered_trace;
                else if (expected!=ordered_trace) std::abort();
            }
        }
    }
    ngb_pending_dpcs=0;
    std::puts("PASS: 128 model scheduler comparisons, including pending callbacks");
}
