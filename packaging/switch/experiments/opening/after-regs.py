"""Do not snapshot eight guest registers for a no-op HLE After callback."""
from pathlib import Path
import re

def observe_bias_pairs(h):
    inc=Path(__file__).with_name('bias-pair.inc').read_text()
    pos='int d3d_hook(int fn)\n{'
    flip='void ngb_direct_timing_flip(unsigned completed)\n{'
    assert h.count(pos)==h.count(flip)==1
    return h.replace(flip,inc+'\n'+flip+'\n    bias_flip(completed);').replace(pos,pos+'\n    if(fn==D3DF_D3DDevice_SetRenderState_ZBias && bias_on) bias_visit(MEM32(esp),MEM32(esp+4));')

def install(p,r,simple_literal=False,constant_groups=False,sync_budget=False,light_before=False,rs_prefix=False,scope_floor=False,push_scratch=False,program_range=False):
    h=(r.parents[2]/'src/d3d/hle.cpp').read_text()
    import sys
    if '--push-overwrite' in sys.argv:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('push-overwrite.py')))['transform'](h)
    if '--transform-page-copy' in sys.argv:
        k='    if (dev) {\n        for (uint32_t t = 0; t < 10; t++) {'
        assert h.count(k)==1
        h=h.replace(k,"""    if (dev && dev <= UINT32_MAX - 0xf43) {
        constexpr unsigned span = 0xf00+17*4-0xc60;
        if (const auto* src = static_cast<const uint8_t*>(DirectPage(dev + 0xc60, span))) {
            static bool reported=false;
            if (!reported) { reported=true; std::fprintf(stderr,"[TRANSFORM_PAGE] used\\n"); }
            static_assert(sizeof(g_state.transforms[0])==64);
            auto* tr=g_state.transforms.data();
            std::memcpy(tr+2,src,2*64);
            std::memcpy(tr+16,src+2*64,4*64);
            std::memcpy(tr+256,src+6*64,4*64);
            std::memcpy(g_state.material.data(),src+0xf00-0xc60,17*4);
            return;
        }
    }
"""+k)
    if '--before-ledger' in sys.argv:
        key='bool Before(int fn, Call c) {'
        assert h.count(key)==1
        h='extern "C" unsigned long long bl_start(int);\nextern "C" void bl_end(int,unsigned long long);\n'+h.replace(key,key+' struct Scope {int id; unsigned long long t; ~Scope(){bl_end(id,t);} } scope{fn,bl_start(fn)};')
    if '--select-budget' in sys.argv:
        case='case D3DF_D3DDevice_SelectVertexShader: {'
        assert h.count(case)==1
        h='extern "C" unsigned long long select_cost_enter();\nextern "C" void select_cost_leave(unsigned long long);\n'+h.replace(case, case+' struct TimedSelect { unsigned long long start=select_cost_enter(); ~TimedSelect(){select_cost_leave(start);} } timed_select;')
    if program_range:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('program-range.py')))['transform'](h)
    if push_scratch:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name("push-scratch.py")))['transform'](h)
    if scope_floor:
        import runpy
        floor=runpy.run_path(str(Path(__file__).with_name('scope-floor.py')))
        h=floor['hle'](h)
    if rs_prefix:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('rs-prefix.py')))['hle'](h)
    if sync_budget:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('sync-budget.py')))['transform'](h)
    if constant_groups:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('constant-groups.py')))['transform'](h)
    if simple_literal:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('simple-literal.py')))['transform'](h)
    if light_before:
        fn='D3DF_D3DDevice_LightEnable'
        a=h.index('    case '+fn+':')
        b=h.index('        break;',a)
        body=h[a:b].split(':\n',1)[1]
        assert 'c.a(0)' in body and set(re.findall(r'c.r\[(\w+)\]',body))=={'EAX'}
        # Reuse the actual case body, including the conditional guest stack read.
        helper='static inline void ApplyLightEnable(uint32_t index,uint32_t stack){\n'+body.replace('c.r[EAX]','index').replace('c.a(0)','R32(stack+4)')+'}\n'
        h=h[:a]+'    case '+fn+': ApplyLightEnable(c.r[EAX],c.r[ESP]);\n'+h[b:]
        h=h.replace('bool Before(int fn, Call c) {',helper+'bool Before(int fn, Call c) {')
        k='extern "C" int d3d_hle_call('
        h=h.replace(k,'extern "C" int ngb_light_before(uint32_t index,uint32_t stack){\n'
                    '    if (!g_started || !g_backend || g_take['+fn+']) return 0;\n'
                    '    if (!g_before_idle['+fn+'].load(std::memory_order_relaxed)) ApplyLightEnable(index,stack);\n'
                    '    return 1;\n}\n'+k)
    a=h.index('void After(int fn, Call c) {'); b=h.index('default:',a)
    live=re.findall(r'^    case (D3DF_\w+):',h[a:b],re.M)
    assert len(live)==4 and re.match(r'default:\s*return;\s*}',h[b:])
    k='extern "C" void d3d_hle_after(int fn, const uint32_t regs[8]) {'
    assert h.count(k)==1 and h[h.index(k):].startswith(k+'\n    if (!g_started) Start();\n    After(fn, Call{const_cast<uint32_t*>(regs)});\n}')
    # Keep the init guard even on the no-register path.
    if '--bias-pair' in sys.argv:
        draw="    if (!g_backend) return;\n    bool measure"
        assert h.count(draw)==1
        h='extern "C" unsigned bias_draw_serial;\n'+h.replace(draw,"    if (!g_backend) return;\n    ++bias_draw_serial;\n    bool measure")
    p.add('hle.cpp',h.replace(k,'extern "C" void ngb_after_empty(void){ if (!g_started) Start(); }\n'+k))
    h=(r/'direct/hooks.c').read_text()
    if '--bias-pair' in sys.argv:
        h=observe_bias_pairs(h)
    if '--select-split' in sys.argv:
        import runpy
        h=runpy.run_path(str(Path(__file__).with_name('select-split.py')))['transform'](h)
    if '--xdk-pc-scope' in sys.argv:
        enter='int d3d_hook(int fn)\n{';ret='    return 1;\n}\n\nvoid d3d_after(';leave='    track_draw_call(fn, 0);\n    if (fn =='
        assert all(h.count(i)==1 for i in (enter,ret,leave))
        h='extern void pc_d3d_enter(void),pc_d3d_leave(void);\n'+h.replace(enter,enter+'\n    pc_d3d_enter();').replace(ret,'    pc_d3d_leave();\n'+ret).replace(leave,'    pc_d3d_leave();\n'+leave)
    if '--xdk-body-ledger' in sys.argv:
        k='if (!took) return 0;'; after='void d3d_after(int fn)\n{'
        assert h.count(k)==1 and h.count(after)==1
        h='extern void xbl_in(int),xbl_out(int);\n'+h.replace(k,'if (!took) {xbl_in(fn); return 0;}').replace(after,after+'\n    xbl_out(fn);')
    if scope_floor:h=floor['hooks'](h)
    if light_before:
        k='    uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};'
        assert h.count(k)==1
        h=h.replace(k,'').replace('    int took = d3d_hle_call(fn, regs);',
            '    if(fn == D3DF_D3DDevice_LightEnable){ extern int ngb_light_before(uint32_t,uint32_t); if(ngb_light_before(eax,esp)) return 0; }\n'+k+'\n    int took = d3d_hle_call(fn, regs);')
    k='    const uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};\n    d3d_hle_after(fn, regs);'
    assert h.count(k)==1
    h=h.replace(k,'    switch(fn){\n'+''.join('    case '+fn+':\n' for fn in live)+'    {\n'+k+'\n    break;\n    }\n    default: {extern void ngb_after_empty(void); ngb_after_empty(); break;}\n    }')
    p.link[p.link.index(str(p.core/'exact-hooks.c.o'))]=p.compile('direct/hooks.c',h,['-include',str(r/'switch_guest_regs.h')])
