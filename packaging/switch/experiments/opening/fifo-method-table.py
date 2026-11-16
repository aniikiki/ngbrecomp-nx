"""Generate immutable lookup entries for aligned NV methods; check the original C."""
from pathlib import Path
import re, subprocess,tempfile
def transform(s):
    h=Path('xboxrecomp/src/nv2a_vk/xemu/nv2a_regs.h').read_text()
    definitions=dict(re.findall(r'^#\s*define (NV097_SET_\w+)\s+(0x[\da-fA-F]+)\s*$',h,re.M))
    def val(n):return int(definitions['NV097_SET_'+n],16)
    ranges=[(val(a),val(b)+delta) for a,b,delta in [('TRANSFORM_PROGRAM','TRANSFORM_CONSTANT',128),('VERTEX_DATA_ARRAY_OFFSET','VERTEX_DATA_ARRAY_FORMAT',64),('ALPHA_TEST_ENABLE','DEPTH_FUNC',4),('VERTEX_DATA4F_M','TEXTURE_OFFSET',0),('TEXTURE_OFFSET','TEXTURE_OFFSET',256)]]
    vs=[next(((hi-m)//4 for lo,hi in ranges if lo<=m<hi),0) for m in range(0,8192,4)]
    assert max(vs)<256
    a=s.index('static unsigned direct_state_words(');b=s.index('\n}',a)+2
    old=s[a:b]
    new='static const unsigned char fifo_run[2048]={\n'+','.join(map(str,vs))+'};\nstatic unsigned direct_state_words(uint32_t method){return method<8192 && !(method&3) ? fifo_run[method>>2] : 0;}'
    # Parser calls with multiples of four only. Confirm all possible input methods and +4 overflow of the 13-bit selector.
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'check.c';path.write_text('#include <stdint.h>\n'+''.join('#define '+n+' '+definitions[n]+'\n' for n in set(re.findall(r'NV097_SET_\w+',old)))+old.replace('direct_state_words','orig')+'\n'+new+'\nint main(void){for(unsigned m=0;m<=8196;m+=4)if(orig(m)!=direct_state_words(m))return 1;return 0;}')
        exe=path.with_suffix('');subprocess.run(['cc',path,'-o',exe],check=True);subprocess.run([exe],check=True)
    return s[:a]+new+s[b:]
