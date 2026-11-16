"""Group the ordered node lookup only until the next original event boundary."""
from pathlib import Path
import sys
here=Path(__file__).resolve().parent;perf=here.parents[1]/'perf';sys.path.insert(0,str(perf))
from native_probe import *
d=BASE/'core-perf/actor-lookup';d.mkdir(exist_ok=True)
if sys.argv[1]=='cross':
 n='recomp_0016.c';s=(BASE/'gen'/n).read_text()
 tag='loc_001CBF20: ; ngb_guest_block_poll();';assert s.count(tag)==1
 s='extern unsigned trial_variant, lookup_nodes;\n'+s.replace(tag,'''loc_001CBF20: ;
    if(trial_variant && !ngb_pending_dpcs && !(ngb_poll_mask & (ngb_poll_mask+1u))){
        unsigned left=ngb_poll_mask-((unsigned)ngb_guest_polls & ngb_poll_mask), used=0;
        while(used<left && esi && !(esi&3) &&
              (esi&4095u)+16u<=ngb_fast_page_bytes[esi>>12]){
            const uint32_t *node=(const uint32_t*)(ngb_fast_ram+(esi&0x7fffffffu));
            uint32_t id=node[3];++used;
            if(id>=ebx){
                ngb_guest_polls+=used;lookup_nodes+=used;
                if(id!=ebx)goto loc_001CBF30;
                goto loc_001CBF32;
            }
            esi=node[1];
        }
        ngb_guest_polls+=used;lookup_nodes+=used;
        if(!esi)goto loc_001CBF30;
    }
    ngb_guest_block_poll();''')
 (d/'fast.c').write_text(s)
 abi=ROOT/'packaging/switch/arm-registers'
 v=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'core-perf/actor-lookup'")
 v=v.replace(" sp.run(c,cwd=w,check=True)"," c[-1]=str(o/'fast.c')\n sp.run(c,cwd=w,check=True)",1)
 v=v[:v.index('with cf.ThreadPoolExecutor')]+"build('recomp_0016.c')"
 exec(compile(v,'lookup-cross','exec'),{'__name__':'__main__'})
 v=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/core-perf/actor-lookup')
 exec(compile(v,'lookup-gates','exec'),{'__name__':'__main__'})
else:
 p=NativeProbe('actor-lookup');p.driver('unsigned lookup_nodes;\n'+(perf/'trial.inc').read_text())
 p.link[p.link.index(str(REGS/'recomp_0016.c.o'))]=str(d/'recomp_0016.c.o')
 s=(RUNTIME/'scene/bridge.c').read_text();k='    ++scene_flips;'
 p.add('scene/bridge.c',s.replace(k,k+' extern void ngb_trial_flip(unsigned,unsigned);extern unsigned lookup_nodes;if(!(scene_flips%120))fprintf(stderr,"[LOOKUP] %u %u\\n",scene_flips,lookup_nodes);ngb_trial_flip(scene_flips,draws);'));p.link.insert(1,'-Wl,--strip-debug');p.finish()
