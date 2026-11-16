"""Generate a guarded simple-render-state scatter from the user's executable."""
import struct
import sys
from pathlib import Path
here = Path(__file__).resolve().parent
perf = here.parents[1] / 'perf'
sys.path.insert(0, str(perf))
from native_probe import NativeProbe, ROOT, RUNTIME

def read_plan():
    b = (ROOT/'game_files/default.xbe').read_bytes()
    u = lambda i: struct.unpack_from('<I', b, i)[0]
    for i in range(u(0x11c)):
        h = u(0x120) - u(0x104) + 56*i
        va, _, raw, n = struct.unpack_from('<4I', b, h+4)
        off = 0x3e9278-va
        if 0 <= off <= n-368:
            return struct.unpack_from('<92I', b, raw+off)
    raise ValueError('State table outside file-backed sections')

verify = '--verify' in sys.argv
p = NativeProbe('method-verify' if verify else 'method-pair')
p.driver((perf/'trial.inc').read_text())
methods = read_plan()
s = (ROOT/'src/d3d/hle.cpp').read_text()
tag = 'void SyncDeferred() {'
s = s.replace(tag, 'extern "C" unsigned trial_variant;\nstatic unsigned plan_hits,plan_misses;\n'+tag)
a = s.index('    for (uint32_t i = 0; i < gpu::kRsDeferredFirst;', s.index(tag))
b = s.index('    for (int s = 0;', a)
loop = s[a:b]
scatter = '\n'.join(f'g_state.simple[{(v&0x1ffc)//4}]=states[{i}];' for i,v in enumerate(methods)
                    if 0x300 <= (v&0x1ffc) < 0x400 or (v&0x1ffc) == 0x1d78)
s = s[:a]+'static_assert(gpu::kRsDeferredFirst==92); static constexpr uint32_t plan[]={'+','.join(map(str,methods))+'};\nif(trial_variant && !std::memcmp(plan,methods,sizeof(plan))){++plan_hits;\n'+('auto ref=g_state.simple;\n'+loop.replace('g_state.simple','ref') if verify else '')+scatter+('\nif(ref!=g_state.simple)std::abort();' if verify else '')+'\n}else{plan_misses+=trial_variant;\n'+loop+'}\n'+s[b:]
s+='\nextern "C" void plan_report(unsigned f){std::fprintf(stderr,"[METHOD_PLAN] %u %u %u\\n",f,plan_hits,plan_misses);}\n'
p.add('hle.cpp',s)
s=(RUNTIME/'scene/bridge.c').read_text()
k='    ++scene_flips;'
assert s.count(k)==1
p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned),plan_report(unsigned);if(!(scene_flips%120))plan_report(scene_flips);ngb_trial_flip(scene_flips,draws);'))
p.link.insert(1,'-Wl,--strip-debug')
p.finish()
