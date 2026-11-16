from pathlib import Path
import subprocess as sp, shlex, json, sys, re
p = Path('/work/build/switch-runtime/core-perf')
p.mkdir(exist_ok=True)
b = p.parent / 'host'
r = Path('/work/packaging/switch/runtime')
mode = sys.argv[1]
actor_modes = ('actor-flow','actor-waves','actor-forward','actor-inputs','actor-tx','actor-batch','actor-worker','actor-fork','actor-snapshot','actor-ahead','actor-args','actor-code','actor-account','actor-native','actor-capture','actor-wave','actor-boundary','actor-journal','actor-intervals','actor-consume','actor-touch','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect','actor-joined-wave')
long_flow = ('task-path','task-chain','task-versions', *actor_modes)
flow_modes = ('task-flow', *long_flow)
out = p / ('pair-' + mode)
out.mkdir(exist_ok=True)
link = json.loads((p / 'exact-link.json').read_text())
cs = sp.check_output(['ninja', '-t', 'commands', 'ngb-runtime-test'], cwd=b, text=True).splitlines()
if mode != 'scheduler':
    groups = sorted((p / ('task-flow' if mode in long_flow else mode)).glob('recomp_*.c.o'))
    if mode in actor_modes:
        overrides = p/('actor-consume' if mode in ('actor-consume','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect','actor-joined-wave') else 'actor-flow')
        groups = [overrides/x.name if (overrides/x.name).exists() else x for x in groups]
        assert sum(x.parent==overrides for x in groups)==2
    assert groups
    allsyms = []
    for alt in groups:
        n = alt.name.replace('.c.o', '.o')
        k = next((i for i, v in enumerate(link) if v.endswith('/' + n)))
        orig = Path(link[k])
        syms = [l.split()[-1] for l in sp.check_output(['nm', '-g', '--defined-only', orig], text=True).splitlines() if l.strip()]
        assert all(s == 'xbe_entry_point' or re.fullmatch('(sub_|d3d_orig_)[0-9A-F]+', s) for s in syms)
        for prefix, path in [('base', orig), ('alt', alt)]:
            rename = out / (prefix + '-' + n + '.syms')
            rename.write_text(''.join((f'{s} {prefix}_{s}\n' for s in syms)))
            obj = out / (prefix + '-' + n)
            shared = p/'pair-task-chain'/obj.name
            if mode in actor_modes and shared.is_file() and (prefix=='base' or alt.parent.name=='task-flow') and shared.stat().st_mtime_ns>=path.stat().st_mtime_ns and rename.read_bytes()==(shared.parent/rename.name).read_bytes():
                # Identical inputs from this build; don't duplicate 45 huge units.
                obj=shared
            else:
                sp.run(['objcopy', '--strip-debug', '--redefine-syms=' + str(rename), path, obj], check=True)
            if prefix == 'base':
                link[k] = str(obj)
            else:
                link.insert(1, str(obj))
        allsyms += syms
    q = out / 'select.c'
    q.write_text('extern unsigned trial_variant;\n' + '\n'.join((f'void base_{s}(void),alt_{s}(void);void {s}(void){{if(trial_variant)alt_{s}();else base_{s}();}}' for s in allsyms)))
    sp.run(['cc', '-O2', '-fno-semantic-interposition', '-c', q, '-o', out / 'select.o'], check=True)
    link.insert(1, str(out / 'select.o'))
s = (p / 'exact-test.c').read_text()
if mode == 'scheduler':
    # Both policies share a process, the same guest code, interrupts and draw path.
    # Only the choice of next runnable worker changes at the frame boundary.
    source = (r / 'workers.inc').read_text()
    marker = '    unsigned parked = running_worker;'
    assert source.count(marker) == 1
    baseline = Path(__file__).with_name('legacy-scheduler.inc').read_text()
    (out / 'workers.inc').write_text(source.replace(marker, baseline + marker))
    (out / 'sched-runtime.inc').write_text((p / 'exact-runtime.inc').read_text())
    s = s.replace('exact-runtime.inc', 'sched-runtime.inc')
if mode in flow_modes:
    # The byte observer owns trial_variant and enables instrumentation for only five frames.
    import runpy
    flow_src = Path(__file__).resolve().parent / 'flow'
    runpy.run_path(str(flow_src/'prepare.py'))['prepare'](
        (p/'exact-runtime.inc').read_text(),(r/'workers.inc').read_text(),out)
    s = s.replace('exact-runtime.inc','flow-runtime.inc')
    if mode in ('actor-fork','actor-snapshot','actor-ahead','actor-code','actor-account','actor-native','actor-capture','actor-wave','actor-boundary','actor-journal','actor-intervals','actor-consume','actor-touch','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect','actor-joined-wave'):
        f=out/'flow-runtime.inc';code=f.read_text()
        mark='void ngb_poll_due(uint64_t ticket)\n{'
        assert code.count(mark)==1
        code=code.replace(mark,mark+'\n    extern unsigned actor_fork_child;if(actor_fork_child)return;')
        code+= '\nunsigned fork_regs(void*p,uint64_t*n){_Static_assert(sizeof(g_regs)<=512,"regs fit");memcpy(p,&g_regs,sizeof(g_regs));*n=entries;return sizeof(g_regs); }\n'
        code+='\nvoid fork_restore(const void*p,uint64_t polls,uint64_t n){memcpy(&g_regs,p,sizeof(g_regs));ngb_guest_polls=polls;entries=n;}\n'
        code+='\nuint64_t fork_entries(void){return entries;}\nunsigned fork_word(unsigned addr){return MEM32(addr); }\n'
        if mode!='actor-joined-wave' and mode in ('actor-boundary','actor-journal','actor-intervals','actor-consume','actor-touch','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect'):code=code.replace(mark,mark+' extern void actor_due(void);actor_due();')
        if mode=='actor-code':
            sym='void ngb_checkpoint(uint32_t va)\n{'
            assert code.count(sym)==1
            code=code.replace(sym,sym+'\n    extern void actor_fork_entry(unsigned);actor_fork_entry(va);')
        if mode in ('actor-consume','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect','actor-joined-wave'):
            code+="""
int actor_service_due(void){return !((ngb_guest_polls+1)&ngb_poll_mask)||ngb_pending_dpcs;}
void actor_quiet_poll(void){ngb_guest_polls++;}
void actor_ordered_entry(unsigned char*r,unsigned bytes){
 uint32_t pc;memcpy(&pc,r+bytes,4);if(pc>>31){current_va=pc&0x7fffffffu;recent[entries++%32]=current_va;}
}
void actor_stress_event(unsigned char*r,unsigned bytes){
 uint32_t pc;memcpy(&pc,r+bytes,4);if(pc>>31){current_va=pc&0x7fffffffu;recent[entries++%32]=current_va;}
 memcpy(&g_regs,r,bytes);ngb_guest_block_poll();
}
void actor_stress_final(const unsigned char*r){memcpy(&g_regs,r,sizeof g_regs);}
void actor_commit_events(unsigned char*t,unsigned stride,unsigned n,const unsigned char*r,uint64_t ticks){
 for(unsigned k=1;k<=n;k++){uint32_t pc;memcpy(&pc,t+(size_t)k*stride+sizeof g_regs,4);
 if(pc>>31){current_va=pc&0x7fffffffu;recent[entries++%32]=current_va;}}
 memcpy(&g_regs,r,sizeof g_regs);ngb_guest_polls=ticks;
}
"""
        if mode=='actor-protect':
            needle='ram = calloc(1, 2u * RAM_BYTES);';assert code.count(needle)==1
            code=code.replace(needle,'ram=aligned_alloc(4096,2u*RAM_BYTES);if(ram)memset(ram,0,2u*RAM_BYTES);')
        f.write_text(code)
    observer = out/'provenance.o'
    observer_source = flow_src/({'actor-wave':'../../experiments/actor-native/wave.c','actor-code':'actor-fork.c','actor-fork':'actor-fork.c','actor-tx':'actor-transactions.c','actor-inputs':'actor-inputs.c','actor-forward':'actor-forward.c','actor-waves':'actor-waves.c','actor-flow':'actors.c','task-path':'path.c','task-chain':'chain.c','task-versions':'versions.c'}.get(mode,'provenance.c'))
    if mode in ('actor-batch','actor-args','actor-worker','actor-snapshot','actor-ahead','actor-account','actor-native','actor-capture','actor-boundary','actor-journal','actor-intervals','actor-consume','actor-touch','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-read-audit','actor-stream','actor-visibility','actor-protect','actor-joined-wave'):
        observer_source=out/'actor-batch.c'
        observer_source.write_bytes(sp.check_output([sys.executable,flow_src/{'actor-joined-wave':'../../experiments/actor-native/joined-wave.py','actor-protect':'../../experiments/actor-native/protect.py','actor-visibility':'../../experiments/actor-native/visibility.py','actor-stream':'../../experiments/actor-native/stream.py','actor-read-audit':'../../experiments/actor-native/read-audit.py','actor-tiles':'../../experiments/actor-native/tiles.py','actor-conflicts':'../../experiments/actor-native/conflicts.py','actor-prepared':'../../experiments/actor-native/prepared.py','actor-cost-live':'../../experiments/actor-native/cost-live.py','actor-packed-live':'../../experiments/actor-native/compact-live.py','actor-stress':'../../experiments/actor-native/consume.py','actor-touch':'../../experiments/actor-native/journal-shadow.py','actor-consume':'../../experiments/actor-native/consume.py','actor-intervals':'../../experiments/actor-native/intervals.py','actor-journal':'../../experiments/actor-native/journal-shadow.py','actor-boundary':'../../experiments/actor-native/checkpoint-shadow.py','actor-capture':'../../experiments/actor-native/capture.py','actor-native':'../../experiments/actor-native/shadow.py','actor-account':'fork-account.py','actor-batch':'actor-batch.py','actor-args':'actor-arguments.py','actor-worker':'worker-proof.py','actor-snapshot':'worker-snapshot.py','actor-ahead':'worker-ahead.py'}[mode],*(['--stress'] if mode=='actor-stress' else [])]))
    sp.run(['cc','-O2','-I'+str(flow_src),'-c',observer_source,'-o',observer],check=True)
    link.insert(1,str(observer))
    if mode=='actor-joined-wave':link.insert(1,str(p.parent/'opt050/actor-wave-state/footprint.o'))
    if mode=='actor-stream':link.insert(1,str(p.parent/'opt050/actor-stream/actor.o'))
    if mode=='actor-read-audit':link.insert(1,str(p.parent/'opt050/actor-reads/actor.o'))
    if mode=='actor-touch':link.insert(1,str(p.parent/'opt050/actor-touch/actor.o'))
    if mode in ('actor-journal','actor-intervals','actor-consume','actor-stress','actor-packed-live','actor-cost-live','actor-prepared','actor-conflicts','actor-tiles','actor-visibility','actor-protect'):link.insert(1,str(p.parent/'opt050/actor-journal/actor.o'))
    if mode=='actor-boundary':link.insert(1,str(p.parent/'opt050/actor-checkpoints/actor.o'))
    if mode=='actor-wave':link.insert(1,str(p.parent/'opt050/actor-sparse/footprint.o'))
    if mode=='actor-capture':link.append('-l:libz.so.1')
    if mode in ('actor-native','actor-capture'):link.insert(1,str(p.parent/'opt050/actor-native/actor.o'))
else:
    marker = 'void __real_ngb_kernel_log'
    assert s.count(marker) == 1
    s = s.replace(marker, Path(__file__).with_name('trial.inc').read_text() + marker, 1)

def obj(name, s, flags):
    c = next((shlex.split(x) for x in cs if x.endswith('/' + name) and (name != 'bridge.c' or '/scene/bridge.c' in x)))
    f = Path(c[-1])
    q = out / name
    q.write_text(s)
    o = str(q) + '.o'
    c[c.index('-o') + 1] = o
    c[c.index('-MF') + 1] = o + '.d'
    c[1:1] = ['-I' + str(f.parent), '-I' + str(p)] + flags
    c[-1] = str(q)
    sp.run(c, cwd=b, check=True)
    return o
link[link.index(str(p / 'exact-runtime_test.c.o'))] = obj('runtime_test.c', s, ['-include', str(r / 'switch_guest_regs.h')])
s = (r / 'scene/bridge.c').read_text().replace('    ++scene_flips;', '    ++scene_flips; extern void ngb_trial_flip(unsigned,unsigned); ngb_trial_flip(scene_flips,draws);')
if mode in flow_modes:
    s=s.replace('extern void ngb_trial_flip(unsigned,unsigned); ngb_trial_flip(scene_flips,draws);',
                'extern unsigned dep_task; extern void dep_flip(unsigned,unsigned); if(scene_flips>=1800 && scene_flips<=1805)dep_flip(scene_flips+1,dep_task);')
if mode in long_flow: s=s.replace('scene_flips<=1805','scene_flips<=1812')
link.insert(1, obj('bridge.c', s, []))
link[link.index('-o') + 1] = str(out / 'replay')
sp.run(link, cwd=b, check=True)
