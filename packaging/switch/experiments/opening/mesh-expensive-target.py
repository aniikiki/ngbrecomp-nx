"""Time each actual indirect material callback only under the measured model caller & middle list."""
from pathlib import Path
import runpy
p=Path(__file__).parent
def transform(s,u):
 s=runpy.run_path(str(p/'material-op-cost.py'))['transform'](s,u)
 k='RECOMP_ENTRY(0x0030BCA0u);';assert s.count(k)==1
 s=s.replace(k,k+' const unsigned selected_parent=MEM32(esp)==0x00307C61u;')
 k='mc_scope=1;';assert s.count(k)==1;s=s.replace(k,'mc_scope=selected_parent;')
 for i in range(5):
    k=f'mc_scope?tree_begin({i}):0';assert s.count(k)==1;s=s.replace(k,'0')
 k='if(mc_scope)mc_target(_icall_target);';assert s.count(k)==1;s=s.replace(k,'')
 k='unsigned ep=tree_epoch;unsigned long long tm=mc_scope?tree_begin(5):0;'
 assert s.count(k)==1;s=s.replace(k,'unsigned slot=_icall_target==0x001D7810u?0:_icall_target==0x001D7800u?1:_icall_target==0x001D7100u?2:3;unsigned ep=tree_epoch;unsigned long long tm=mc_scope?tree_begin(slot):0;')
 k='tree_end(5,ep,tm)';assert s.count(k)==1;s=s.replace(k,'tree_end(slot,ep,tm)')
 return s
runpy.run_path(str(p/'model-copy.py'))['build']('mesh-expensive-target',[(False,[28])],transform)
