"""Collect exact within-function label sequences; do not record or replay guest data."""
from pathlib import Path
import runpy,re
def transform(s,u):
 a=s.index('void sub_0030BCA0(void)\n{');b=s.index('\n}',a);body=s[a:b]
 labels=re.findall(r'^loc_([0-9A-F]+): ;',body,re.M);assert len(labels)==len(set(labels))==88
 body=body.replace('    RECOMP_ENTRY','    unsigned epoch=mp_epoch, len=0; unsigned char path[192];\n    RECOMP_ENTRY',1)
 for i,v in enumerate(labels):body=body.replace('loc_'+v+': ;','loc_'+v+': ; if(epoch<120 && len<193){if(len<192)path[len]='+str(i)+'; ++len;}')
 assert body.count('esp += 4; return;')==1
 body=body.replace('esp += 4; return;','if(epoch<120)mp_finish(epoch,path,len); esp += 4; return;')
 return 'extern unsigned mp_epoch; extern void mp_finish(unsigned,const unsigned char*,unsigned);\n'+s[:a]+body+s[b:]
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('mesh-paths',[(False,[28])],transform)
