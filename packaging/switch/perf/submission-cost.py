"""Destructive-to-pixels offline experiment, never linked into a playable NRO.
Keep guest draw calls and FIFO work. Omit only ordinary host drawing on
balanced alternating frames to estimate the headroom of a new command path."""
from pathlib import Path
from native_probe import NativeProbe, ROOT as root, RUNTIME as rt
probe=NativeProbe('submission-cost')
trial=(Path(__file__).with_name('trial.inc')).read_text().replace('    unsigned start = frame <= 120 ? 32 : 1680;', '    unsigned start = 1680;')
probe.driver(trial)
s=(root/'src/d3d/hle.cpp').read_text()
s='extern "C" { extern unsigned trial_variant; unsigned omitted,observed; }\nstatic bool checking_visibility;\n'+s
tag='    if (!g_backend) return;\n    bool measure ='
assert s.count(tag)==1
s=s.replace(tag,'''    if (!g_backend) return;
    static const bool after_sync=std::getenv("NGB_COST_AFTER_SYNC")!=nullptr;
    ++observed;
    if(trial_variant && !checking_visibility && !after_sync){++omitted;return;}
    bool measure =''')
tag='    uint64_t record_start = measure ?'
s=s.replace(tag,'    if(trial_variant && !checking_visibility && after_sync){++omitted;return;}\n'+tag)
s=s.replace('if (g_backend && !g_mirror) g_backend->VisibilityBegin();','if (g_backend && !g_mirror){checking_visibility=true;g_backend->VisibilityBegin();}')
s=s.replace('if (g_backend && !g_mirror && page) g_backend->VisibilityEnd(page + (g_vis_index & 0xFF) * 16);','if (g_backend && !g_mirror && page){g_backend->VisibilityEnd(page + (g_vis_index & 0xFF) * 16);checking_visibility=false;}')
probe.add('hle.cpp',s)
s=(rt/'scene/bridge.c').read_text();tag='    ++scene_flips;'
s=s.replace(tag,tag+''' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned omitted,observed,trial_variant;
    if(scene_flips>1680 && scene_flips<=1920)fprintf(stderr,"[OMIT] %u %u %u %u\\n",scene_flips,trial_variant,omitted,observed);
    omitted=observed=0;ngb_trial_flip(scene_flips,draws);''')
probe.add('scene/bridge.c',s);probe.finish()
