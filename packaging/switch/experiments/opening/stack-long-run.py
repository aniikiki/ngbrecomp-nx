"""Amortize one end-of-page check over a whole run of four or more stack transfers."""
from pathlib import Path
import re,runpy
regs=r'(?:eax|ecx|edx|ebx|ebp|esi|edi)'
pat=re.compile('|'.join(r'(?:^    '+op+r'32\(esp, '+regs+r'\);\n){4,}' for op in ('PUSH','POP')),re.M)
def replace(m):
    original=m[0]
    seq=re.findall(r'32\(esp, (\w+)\)',original)
    push='PUSH' in original
    n=len(seq)
    ops=[]
    for i,r in enumerate(seq):
        word=f'q[{n-1-i if push else i}].v'
        ops.append(f'{word}={r};' if push else f'{r}={word};')
    return ('    { uint32_t a='+ (f'esp-{4*n}u' if push else 'esp')+
            f'; if (__builtin_expect((uint64_t)a+{4*(n-1)}u < reg_ends[a>>12],1)) {{'
            'struct __attribute__((packed,may_alias)) W {uint32_t v;};'
            'volatile struct W *q=(volatile struct W*)(ngb_fast_ram+(a&0x7fffffffu));'+
            ''.join(ops)+('esp=a;' if push else f'esp=a+{4*n}u;')+
            '} else {\n'+original+'}}\n')
def transform(s,u):
    s,n=pat.subn(replace,s)
    assert n=={1:41,9:21,15:27}[u],(u,n)
    return s
if __name__=='__main__':
    runpy.run_path(str(Path(__file__).with_name('model-copy.py')))['build']('stack-long-run',[(False,[1,9,15])],transform)
