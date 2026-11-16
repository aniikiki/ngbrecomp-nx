"""Positive control for chapter encounter telemetry: same original damage
routine, noninteractive retail combat. Capture both attacker and target."""
from pathlib import Path
import sys
h=Path(__file__).resolve().parent;perf=h.parents[1]/'perf';sys.path.insert(0,str(perf));from native_probe import *
p=NativeProbe('damage-control');p.link.insert(1,'-Wl,--strip-debug')
s=(perf/'trial.inc').read_text()
s+='''static unsigned hero_dealt,hero_received,other_hits;
void fight_damage(unsigned target,unsigned attacker,unsigned before,unsigned after){
 if(before<=after)return;
 if(attacker==0x4b4e50 && target!=attacker)++hero_dealt;
 else if(target==0x4b4e50 && attacker!=target)++hero_received;else ++other_hits;
 fprintf(stderr,"[HIT_CONTROL] target=%08x attacker=%08x hp=%u->%u dealt=%u received=%u other=%u\\n",
 target,attacker,before,after,hero_dealt,hero_received,other_hits);
}
'''
p.driver(s);i=next(i for i,v in enumerate(p.link) if v.endswith('/recomp_0017.o'));p.link[i]=str(BASE/'opt050/fight2/damage.o');p.finish()
