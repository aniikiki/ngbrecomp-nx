"""Combine page checks for consecutive scalar moves from/to one base.
Preserve volatile accesses, order and the original fallback; no value cache."""
import re,sys,os
from pathlib import Path
base=Path('build/switch-runtime')
reg=r'e(?:ax|bx|cx|dx|si|di|bp|sp)'
addr=rf'MEM(8|16|32)\(({reg})(?: \+ (0x[0-9a-fA-F]+|[0-9]+))?\)'
op=re.compile(rf'    (?:({reg}) = ({addr})|({addr}) = ({reg}));\n')
def transform(s):
 lines=s.splitlines(True);out=[];i=0;groups=[]
 while i<len(lines):
    seq=[];j=i
    while j<len(lines) and (m:=op.fullmatch(lines[j])):
        width,b,o=(m[3],m[4],m[5]) if m[1] else (m[7],m[8],m[9])
        off=int(o or '0',0)
        if seq and b!=seq[0][1]:break
        seq.append((width,b,off,m));j+=1
        if m[1]==b:break
    if len(seq)<2:out.append(lines[i]);i+=1;continue
    b=seq[0][1] # The lookahead may belong to the NEXT base.
    lo=min(x[2] for x in seq);hi=max(x[2]+int(x[0])//8 for x in seq)
    if hi-lo>4096:out.append(lines[i]);i+=1;continue
    out.append(f'    {{ uint32_t va={b}+{lo}u; if (__builtin_expect((va&4095u)+{hi-lo}u<=ngb_fast_page_bytes[va>>12],1)) {{ unsigned char *p=ngb_fast_ram+(va&0x7fffffffu);\n')
    for w,_,o,m in seq:
        a=f'*(volatile uint{w}_t *)(p+{o-lo})'
        out.append(f'        {m[1]} = {a};\n' if m[1] else f'        {a} = {m[10]};\n')
    out+=['    }else{\n',*lines[i:j],'    } }\n'];groups.append((i,len(seq)));i=j
 return ''.join(out),groups
def opening_only(s):
 # Freeze the selection from the verified 31..120 entry histogram, never train
 # on timing results. Entry counts do not imply each branch is reached.
 hot=set('00328232 003066B0 00317DC0 0030BCA0 0030B7E0 0030C2A0 001CB730 001CBED0 00305870 0030C1A0 001CACA0 003078B0 00308D80 00305D60 001CB510 001D6180 001CBD00 00305490 001CBBF0 001C94F0 00307B80 001CB3B0 001D9610 001D9D20'.split())
 anchors=list(re.finditer(r'(?m)^void (\w+)\(void\)\n\{',s));out=[];groups=[];last=0
 for i,m in enumerate(anchors):
    if m[1].removeprefix('sub_') not in hot:continue
    end=anchors[i+1].start() if i+1<len(anchors) else len(s)
    out.append(s[last:m.start()]);body,g=raw_transform(s[m.start():end]);out.append(body);groups+=g;last=end
 return ''.join(out)+s[last:],groups
raw_transform=transform
if __name__=='__main__':
 if '--opening-only' in sys.argv:transform=opening_only
 src=Path(__file__).with_name('vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
 exec(compile('if True:'+src.replace('original vector moves','original scalar moves').replace('opening-vector-span','opening-scalar-run'),'scalar-run-build','exec'))
