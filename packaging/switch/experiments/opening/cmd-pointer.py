"""Reuse ordinary RAM pointer across three command-loop backedges."""
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
    extra=f"""
    if ((ecx&4095u)+4<=ngb_fast_page_bytes[ecx>>12]) {{
        volatile uint32_t *ptr=(volatile uint32_t *)(ngb_fast_ram+(ecx&0x7fffffffu));
        _fa=*ptr; _fb=0x9000000Du; _fas=(int32_t)_fa; _fbs=(int32_t)_fb;
        if(_fa!=_fb) {{
            uint64_t ticket=++ngb_guest_polls;
            if(!(ticket & ngb_poll_mask)||ngb_pending_dpcs){{ngb_poll_due(ticket); edx=MEM32(ecx);}}
            else edx=*ptr;
            goto cmd_loaded_{head};
        }}
    }} else {{
"""
    s=s[:a]+f'loc_{back}: ;'+extra+old.split(': ;',1)[1]+'\n    }'+s[b:]
 return s,None
if __name__=='__main__':
 src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('units=[16,28,29]','units=[10]').replace('opening-vector-span','opening-cmd-pointer'),'box-reuse-build','exec'))
