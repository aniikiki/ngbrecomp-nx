"""Walk a contiguous ordinary-page run of unhandled words in original order."""
from pathlib import Path
import re,os,sys
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 # The ordinary-page pointer is valid across the backedge only if no service
 # runs. Keep both volatile word reads and all observable guest register writes.
 for head,back in [('00149CF0','00149F19'),('00149F41','0014A15B'),('0014A183','0014A386')]:
    k=f'loc_{head}: ; ngb_guest_block_poll();\n    edx = MEM32(ecx);'
    assert s.count(k)==1
    s=s.replace(k,k+f'\ncmd_loaded_{head}: ;')
    a=s.index(f'loc_{back}: ;');b=s.index('\n\n',a)
    old=s[a:b]
    assert old.count('(uint32_t)(MEM32(ecx))')==1 and f'goto loc_{head};' in old
    after=s[b:].split(': ;',1)[0].strip()
    assert after.startswith('loc_') and len(after)==12
    bias={'00149CF0':0x90000001,'00149F41':0x90000005,'0014A183':0x90000009}[head]
    extra=f"""
    {{
        unsigned off=ecx&4095u, bytes=ngb_fast_page_bytes[ecx>>12];
        if(!(off&3) && off+4<=bytes){{
            volatile uint32_t *ptr=(volatile uint32_t *)(ngb_fast_ram+(ecx&0x7fffffffu));
            unsigned words=(bytes-off)/4;
            do {{
                _fa=*ptr; _fb=0x9000000Du; _fas=(int32_t)_fa; _fbs=(int32_t)_fb;
                if(_fa==_fb)goto {after};
                uint64_t ticket=++ngb_guest_polls;
                if(!(ticket & ngb_poll_mask)||ngb_pending_dpcs){{ngb_poll_due(ticket); edx=MEM32(ecx); goto cmd_loaded_{head};}}
                edx=*ptr++;
                if(edx-0x{bias:X}u<=3u)goto cmd_loaded_{head};
                edx-=0x{bias:X}u;ecx+=4;
            }} while(--words);
            goto loc_{back};
        }}
    }}
"""
    s=s[:a]+f'loc_{back}: ;'+extra+old.split(': ;',1)[1]+s[b:]
 return s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-cmd-page-run'),'box-reuse-build','exec'))
