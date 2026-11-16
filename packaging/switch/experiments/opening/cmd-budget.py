"""Sample one in seven whole interpreter invocations, all three passes inclusive. Never skip side effects or alter the answer."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='RECOMP_ENTRY(0x00149CB0u);';assert s.count(k)==1
 a=s.index(k);b=s.index('\n}',a);body=s[a:b]
 assert body.count('return;')==4
 body=body.replace(k,"unsigned bf=cmd_window;unsigned long long bt=0;if(bf && !(cmd_seq++%7))bt=cmd_cpu(); "+k)
 body=body.replace('return;', 'if(bt && bf==cmd_window){cmd_ticks+=cmd_cpu()-bt;++cmd_samples;} return;')
 return 'extern unsigned cmd_window,cmd_seq,cmd_samples;extern unsigned long long cmd_cpu(void),cmd_ticks;\n'+s[:a]+body+s[b:],None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-cmd-budget'),'box-reuse-build','exec'))
