"""Measure inclusive CPU time of each ordered scan, once per whole traversal. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 sites=[('2E3B89',('2E3BB6','2E3BB8')),('2E40BA',('2E40E9','2E40EB')),('2E7EF9',('2E7F24','2E7F2A'))]
 for i,(entry,exits) in enumerate(sites):
    k=f'loc_00{entry}: ;'
    pos=s.index(k)
    func=s.rindex('RECOMP_ENTRY(',0,pos)
    s=s[:func]+'unsigned bf=0; unsigned long long bt=0; '+s[func:]
    assert s.count(k)==1
    s=s.replace(k,k+' bf=box_window;if(bf)bt=box_cpu();')
    for ex in exits:
        k=f'loc_00{ex}: ;';assert s.count(k)==1
        s=s.replace(k,k+f' if(bf && bf==box_window){{box_ticks[{i}]+=box_cpu()-bt;++box_runs[{i}];}}')
 return 'extern unsigned box_window,box_runs[3];extern unsigned long long box_cpu(void),box_ticks[3];\n'+s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[26]').replace('opening-vector-span','opening-box-budget'),'box-reuse-build','exec'))
