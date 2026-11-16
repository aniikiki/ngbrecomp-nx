from pathlib import Path
import sys
root=Path('/work');sys.path.insert(0,str(root/'packaging/switch/perf'))
from native_probe import NativeProbe,BASE,REGS,RUNTIME
live='--live' in sys.argv
pursue=live or '--pursue' in sys.argv
climb='--climb' in sys.argv or pursue
p=NativeProbe('chapter-live' if live else 'chapter-pursue' if pursue else 'chapter-climb' if climb else 'chapter-ledge');p.link.insert(1,'-Wl,--strip-debug');d=BASE/'opt050/fight2'
story=(RUNTIME/'story_test.inc').read_text().replace('    unsigned at=tick++%144;', '    if(fight_live){fight_pad();return;}\n    unsigned at=tick++%144;').replace('ngb_stop("verified first chapter player control",tick);','fight_live=1;')
pad=(Path(__file__).with_name('pursue.inc' if pursue else 'climb.inc' if climb else 'ledge.inc')).read_text()
if live:
 pad=pad.replace('if(t>3600)','if(t>24000)').replace('if(v<=5||v>9999)','if(!v||v>9999)').replace(' ngb_ohci_pad_sample(button,xaxis,yaxis,0,0);',(Path(__file__).with_name('live.inc')).read_text())
s=(REGS/'host-driver.c').read_text().replace('#include "story_test.inc"',pad+'\n'+story)
p.link[p.link.index(str(p.core/'exact-runtime_test.c.o'))]=p.compile('runtime_test.c',s,['-I'+str(REGS),'-I'+str(RUNTIME),'-include',str(RUNTIME/'switch_guest_regs.h'),'-DNGB_RIGID_CLIP','-DNGB_REGISTER_PACKAGE'])
old=next(i for i,v in enumerate(p.link) if v.endswith('/recomp_0017.o'));p.link[old]=str(d/'damage.o');p.finish()
