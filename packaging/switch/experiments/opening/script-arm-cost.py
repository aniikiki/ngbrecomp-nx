"""Time the work *after* the top-level script command target has actually been read."""
from pathlib import Path
import re,runpy
p=Path(__file__).parent
targets=(0x16516,0x165c1,0x1634e,0x1655a,0x16386,0x165e0,0x16ddf,0x1632e,0x16a96,0x1653b,0x178ea,0x17803,0x18189,0x1636a,0x16ba1,0x18290,0x163c0,0x16673)
def transform(s,u):
 a=s.index('void sub_00016300(void)\n{');b=s.index('\n}',a)
 body=s[a:b];k='RECOMP_ENTRY(0x00016300u);'
 assert body.count(k)==1
 body=body.replace(k,k+' unsigned arm=18,ep=0;unsigned long long tm=0;')
 k='uint32_t _jt = MEM32(eax * 4 + 0x186A4);';assert body.count(k)==1
 cases=''.join(f'case {v}:arm={i};break;' for i,v in enumerate(targets))
 body=body.replace(k,k+' switch(_jt){'+cases+'default:arm=18;}ep=tree_epoch;tm=tree_begin(arm);')
 assert body.count('return;')==6
 body=body.replace('return;','if(tm)tree_end(arm,ep,tm);return;')
 return 'extern unsigned tree_epoch; extern unsigned long long tree_begin(unsigned);extern void tree_end(unsigned,unsigned,unsigned long long);\n'+s[:a]+body+s[b:]
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('script-arm-cost',[(False,[0])],transform)
