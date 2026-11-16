"""Hoist mapping of three operands in one matrix row; retain volatile ordering."""
import re
from pathlib import Path
def transform(s):
    k='loc_00303FB0: ; ngb_guest_block_poll();'
    assert s.count(k)==1
    a=s.index(k)+len(k);b=s.index('    _fb = (uint32_t)(8)',s.index('    MEMF(edx) = xmm0.f[0];',s.index('edx = edx + 4;',a)),)
    old=s[a:b]
    # Keep the guest instructions that advance edx. Express each output
    # relative to its entry address; none of the inputs advance in this span.
    delta=0;new=[]
    for l in old.splitlines(True):
        def replace(m):
            reg=m[1];off=int(m[2] or '0',0)
            idx={'ecx':off,'eax':off+4,'edx':delta+off}[reg]
            assert 0<=idx<{'ecx':44,'eax':12,'edx':12}[reg] and idx%4==0
            return f'({reg}_words[{idx//4}])'
        new.append(re.sub(r'MEMF\((e[acd]x)(?: \+ (-?(?:0x[0-9A-F]+|\d+)))?\)',replace,l))
        if 'edx = edx + 4;' in l:delta+=4
    assert delta==8 and sum(x.count('_words[') for x in new)==21 and not any('MEMF' in x for x in new)
    return s[:a]+'''
    {
        uint32_t a0=eax-4u;
        if(((a0|ecx|edx)&3u)==0 &&
           (a0&4095u)+12u<=ngb_fast_page_bytes[a0>>12] &&
           (ecx&4095u)+44u<=ngb_fast_page_bytes[ecx>>12] &&
           (edx&4095u)+12u<=ngb_fast_page_bytes[edx>>12]){
            volatile float *eax_words=(volatile float *)(ngb_fast_ram+(a0&0x7fffffffu));
            volatile float *ecx_words=(volatile float *)(ngb_fast_ram+(ecx&0x7fffffffu));
            volatile float *edx_words=(volatile float *)(ngb_fast_ram+(edx&0x7fffffffu));
'''+''.join(new)+'        }else{'+old+'        }\n    }\n'+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'tree-level.py').read_text().split("if __name__=='__main__':",1)[1]
    s=s.replace('tree-level','row-three').replace('0028','0027')
    # page-hot-o3 gained loop_ira since the original builder
    s=s.replace('d=(base/','loop_ira=False;d=(base/')
    exec(compile('if True:'+s,'row-three-build','exec'))
