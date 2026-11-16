"""Verify the whole live method table before applying constant-offset transfers."""
import sys,struct
from pathlib import Path
def generate(words,old):
    runs=[]
    for i,raw in enumerate(words):
        m=raw&0x1ffc
        if not(0x300<=m<0x400 or m==0x1d78):continue
        dst=m//4
        if runs and (i,dst)==(runs[-1][0]+runs[-1][2],runs[-1][1]+runs[-1][2]):
            runs[-1][2]+=1
        else:runs.append([i,dst,1])
    assign='\n'.join(f'        std::memcpy(g_state.simple.data()+{dst},states+{src},{n*4});' for src,dst,n in runs)
    return '    static constexpr uint32_t expected_methods[]={'+','.join(hex(w)+'u' for w in words)+'};\n    static_assert(sizeof(expected_methods)==gpu::kRsDeferredFirst*4);\n    if (!std::memcmp(methods,expected_methods,sizeof(expected_methods))) {\n'+assign+'\n    } else {\n'+old+'    }\n'
def transform(s):
    sys.path.insert(0,str(Path.cwd()/'xboxrecomp/tools/abi_analysis'))
    from xbe_min import XbeFile
    va=0x3e9278
    assert 'kSimpleEncode = 0x3E9278' in s
    words=struct.unpack('<92I',XbeFile(Path('game_files/default.xbe')).read_bytes_at_va(va,368))
    a=s.index('    for (uint32_t i = 0; i < gpu::kRsDeferredFirst; i++)')
    b=s.index('    for (int s = 0;',a)
    return s[:a]+generate(words,s[a:b])+s[b:]
