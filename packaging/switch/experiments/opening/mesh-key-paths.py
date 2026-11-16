"""Bind the measured basic-block trace to the guest mesh pointer already loaded in ESI."""
from pathlib import Path
import runpy
d=Path(__file__).parent
def transform(src,u):
 s=runpy.run_path(str(d/'mesh-paths.py'))['transform'](src,u)
 s=s.replace('mp_finish(unsigned,const unsigned char*,unsigned)','mp_finish(unsigned,unsigned,const unsigned char*,unsigned)').replace('len=0; unsigned char path','len=0,key=0; unsigned char path').replace('mp_finish(epoch,path,len)','mp_finish(epoch,key,path,len)')
 k='    edi = esi;\n    MEMF(0x44B3C4)';assert s.count(k)==1
 return s.replace(k,'    edi = esi; key=esi;\n    MEMF(0x44B3C4)')
if __name__=='__main__':runpy.run_path(str(d/'model-copy.py'))['build']('mesh-key-paths',[(False,[28])],transform)
