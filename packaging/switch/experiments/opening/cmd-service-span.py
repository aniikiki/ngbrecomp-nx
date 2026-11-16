"""Scan original commands up to the first page or scheduling boundary.
Read in order; no speculative reads beyond a terminator or active opcode."""
from pathlib import Path
import runpy
p=Path(__file__).parent
cases=[('00149CF0','00149F19','00149D04','00149F25'),('00149F41','0014A15B','00149F55','0014A167'),('0014A183','0014A386','0014A197','0014A392')]
def transform(s,u):
 for i,(head,back,dispatch,after) in enumerate(cases):
  k='loc_'+back+': ;';assert s.count(k)==1
  code='''
    {uint32_t address=ecx, end=reg_ends[address>>12], mask=ngb_poll_mask;
     uint64_t ticket=ngb_guest_polls;
     if(!(address&3u) && end>address && !(mask&(mask+1u)) && !ngb_pending_dpcs){
      unsigned n=(end-address-1)/4+1, until=mask-((uint32_t)ticket&mask);
      if(n>until)n=until;
      if(n>=2){
       volatile const uint32_t *ptr=(volatile const uint32_t*)(ngb_fast_ram+(address&0x7fffffffu));
       for(unsigned j=0;j<n;++j){
        _fa=*ptr;_fas=(int32_t)_fa;_fb=0x9000000Du;_fbs=(int32_t)_fb;
        if(_fa==_fb){ngb_guest_polls=ticket+j;goto AFTER;}
        edx=*ptr++ - BIAS;ecx+=4;
        if(edx<=3u){ngb_guest_polls=ticket+j+1;_fa=edx;_fas=(int32_t)edx;_fb=3;_fbs=3;goto DISPATCH;}
       }
       ngb_guest_polls=ticket+n;goto BACK;
      }
     }}
'''
  s=s.replace(k,k+code.replace('AFTER','loc_'+after).replace('BACK','loc_'+back).replace('DISPATCH','loc_'+dispatch).replace('BIAS',hex(0x90000001+i*4)+'u'))
 return s
if __name__=='__main__':runpy.run_path(str(p/'model-copy.py'))['build']('cmd-service-span',[(True,[10])],transform)
