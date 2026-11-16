"""Dispatch by low bits of the *loaded* guest branch address. Check the full
address within each bucket and fall through to the original indirect fallback."""
from pathlib import Path
import re,sys,os
pat=re.compile(r'(?P<header>    \{ uint32_t _jt = MEM32\([^\n]+? /\* switch: \d+ entries, (\d+) targets \*/\n)(?P<arms>(?:    if \(_jt == 0x[0-9A-F]+u\) goto loc_[0-9A-F]+;\n)+)')
def transform(s):
    def one(m):
        arms=m['arms'].splitlines()
        assert len(arms)==int(m[2])
        if len(arms)<16:return m[0]
        n=1<<(len(arms)-1).bit_length()
        groups={}
        for arm in arms:
            v,l=re.search(r'0x(\w+)u\) goto loc_(\w+);',arm).groups()
            assert v==l
            groups.setdefault(int(v,16)%n,[]).append(arm)
        return m['header']+f'    switch (_jt & {n-1}u) {{\n'+''.join(f'    case {k}:\n'+'\n'.join(a)+'\n        break;\n' for k,a in groups.items())+'    }\n'
    return pat.sub(one,s)
if __name__=='__main__':
    root=Path('build/switch-runtime')
    units=[0,2]
    if '--build' not in sys.argv:
        for u in units:
            s=(root/'gen'/f'recomp_{u:04}.c').read_text();t=transform(s)
            from collections import Counter
            checks=r'if \(_jt == [^)]+\) goto loc_\w+;'
            assert Counter(re.findall(checks,s))==Counter(re.findall(checks,t))
            print(u,'converted sites',t.count('switch (_jt & '))
        sys.exit()
    d=(root/'core-perf/opening-jump-buckets').resolve();d.mkdir(exist_ok=True)
    abi=Path('/work/packaging/switch/arm-registers')
    for u in units:
        n=f'recomp_{u:04}.c';(d/n).write_text(transform((root/'gen'/n).read_text()))
    os.environ['NGB_REG_OUT']=str(d)
    s=(abi/'compile.py').read_text()
    s=re.sub(r'^ns=\[[\d,]+\]$', 'ns=list(range(47))',s,flags=re.M)
    num=r'(?:sub_|d3d_orig_)[0-9A-F]+'
    s=s.replace(num,'(?:'+num+'|xbe_entry_point)')
    s=s[:s.index("f=o/'entry.S'")].replace('ex.map(build,units)','ex.map(build,'+repr([f'recomp_{i:04}.c' for i in units])+')')
    s=s.replace(' sp.run(c,cwd=w,check=True)'," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\n sp.run(c,cwd=w,check=True)")
    exec(compile(s,'jump-buckets','exec'),{})
    exec(compile((abi/'gates.py').read_text(),'jump-gates','exec'),{})
    for f in [*d.glob('recomp_*.s'),*d.glob('recomp_*.c')]:f.unlink()
