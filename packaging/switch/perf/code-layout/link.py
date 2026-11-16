from pathlib import Path
import subprocess,sys
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent))
from native_probe import NativeProbe,RUNTIME,BASE
p=NativeProbe('code-layout')
d=BASE/'opt050/codetrace/gum'
p.driver('')
s=(RUNTIME/'scene/bridge.c').read_text();tag='    ++scene_flips;'
assert s.count(tag)==1
p.add('scene/bridge.c',s.replace(tag,tag+' extern void layout_frame(unsigned); if(scene_flips>=1799 && scene_flips<=1803)layout_frame(scene_flips+1);'))
o=p.out/'trace.o'
subprocess.run(['cc','-O2','-I'+str(d),'-c',here/'trace.c','-o',o],check=True)
# Some host linker commands finish with as-needed libraries. Keep Gum and its
# dependencies after the observer, not before it.
p.link.extend([str(o),str(d/'libfrida-gum.a'),'-ldl','-lm','-lresolv','-latomic','-pthread'])
p.finish()
