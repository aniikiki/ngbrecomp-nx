"""Native texture-stage table update when the guest index selects one of the four image-resident slots."""
from pathlib import Path
import runpy
fast='''
    if (ebp < 4u && ngb_fast_ram) {
        edi = MEM32(0xC0EBB0);
        eax = ebp << 7;
#define MS_WORD(base,idx) (*(volatile uint32_t*)(ngb_fast_ram+(base)+(idx)))
        if (MS_WORD(0x9779A8u,eax) != esi) {
            ecx = MEM32(0x3D83D0) | 0x800u;
            MS_WORD(0x9779A8u,eax) = esi;
            MEM32(0x3D83D0) = ecx;
            MS_WORD(0x3D5D40u,eax) = esi;
        }
        if (MS_WORD(0x9779B8u,eax) != esi) {
            ecx = MEM32(0x3D83D0) | 0x800u;
            MS_WORD(0x9779B8u,eax) = esi;
            MEM32(0x3D83D0) = ecx;
            MS_WORD(0x3D5D50u,eax) = esi;
        }
        eax = MS_WORD(0x977968u,ebp*4u);
#undef MS_WORD
        if (eax) goto loc_0030C009;
        goto loc_0030C01D;
    }
'''
def transform(s,u):
 k='loc_0030BFA7: ;';assert s.count(k)==1
 return s.replace(k,k+fast)
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('mesh-stage',[(False,[28])],transform)
