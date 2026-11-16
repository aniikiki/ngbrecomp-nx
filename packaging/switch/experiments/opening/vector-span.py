"""One page validation for consecutive 16-byte moves on a single base. Keep
the load/store order, every XMM result, and the original slow path verbatim."""
import re,sys,os
from pathlib import Path
base=Path('build/switch-runtime')
load=re.compile(r'    (xmm[0-7]) = XMM_MEM\((e\w{2})(?: \+ (0x[0-9a-fA-F]+))?\); /\* mov[au]ps \*/\n')
store=re.compile(r'    XMM_STORE\((e\w{2})(?: \+ (0x[0-9a-fA-F]+))?, (xmm[0-7])\); /\* mov[au]ps \*/\n')
def transform(s):
    out=[];lines=s.splitlines(True);i=0;groups=[]
    while i<len(lines):
        for op in (load,store):
            seq=[];j=i
            while j<len(lines) and (m:=op.fullmatch(lines[j])):
                reg,b,o=m.groups() if op is load else (m[3],m[1],m[2])
                o=int(o or '0',0)
                if seq and (seq[0][1]!=b or seq[-1][2]+16!=o):break
                seq.append((reg,b,o));j+=1
            if len(seq)<2:continue
            off=seq[0][2];n=len(seq)*16
            out.append(f'    {{ uint32_t va={b}+{off}u; if (__builtin_expect((va&4095u)+{n}u<=ngb_fast_page_bytes[va>>12],1)) {{ unsigned char *p=ngb_fast_ram+(va&0x7fffffffu);\n')
            for reg,_,o in seq:
                args=f'&{reg},p+{o-off}' if op is load else f'p+{o-off},&{reg}'
                out.append(f'        __builtin_memcpy({args},16);\n')
            out+=['    }else{\n',*lines[i:j],'    } }\n'];groups.append((i,len(seq)));i=j;break
        else:out.append(lines[i]);i+=1
    return ''.join(out),groups

if __name__=='__main__':
    units=[16,28,29]
    if '--build' not in sys.argv:
        for u in units:
            s=(base/'gen'/f'recomp_{u:04}.c').read_text();_,g=transform(s)
            print(u,'groups',len(g),'original vector moves',sum(n for _,n in g))
        sys.exit()
    abi=Path('/work/packaging/switch/arm-registers');d=(base/'core-perf/opening-vector-span').resolve();d.mkdir(exist_ok=True)
    names=[f'recomp_{u:04}.c' for u in units]
    for n in names:(d/n).write_text(transform((base/'gen'/n).read_text())[0])
    os.environ['NGB_REG_OUT']=str(d)
    s=(abi/'compile.py').read_text()
    s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
    num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
    s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
    s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)','ex.map(build,'+repr(names)+')')
    s=s.replace(' sp.run(c,cwd=w,check=True)'," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)")
    exec(compile(s,'vector-span','exec'),{})
    exec(compile((abi/'gates.py').read_text(),'vector-span-gates','exec'),{})
    for f in [*d.glob('recomp_*.s'),*(d/n for n in names)]:f.unlink()
