"""Count visits, first boxes and hits at each direct caller. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 sites=[0x2E3B9E,0x2E40D1,0x2E7F0D]
 for i,ret in enumerate(sites):
    k=f'PUSH32(esp, 0x{ret:08X}u); RECOMP_ABI_CALL(0x002E4470u, sub_002E4470);'
    assert s.count(k)==1
    s=s.replace(k,f'if(scan_active){{ ++scan_n[{i}][0];scan_n[{i}][1]+=(esi==0x9284C0); }} '+k+f' if(scan_active)scan_n[{i}][2]+=(LO8(eax)!=0);')
 return 'extern unsigned scan_active,scan_n[3][3];\n'+s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[26]').replace('opening-vector-span','opening-box-scan'),'box-reuse-build','exec'))
