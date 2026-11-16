"""Resolve sampled AArch64 scalar/pair address operands offline."""
import sys,re
from bisect import bisect_right
from pathlib import Path
from collections import Counter
def address(args,r):
    m=re.search(r'\[([^\]]+)\]',args)
    if not m:return None
    a=[x.strip() for x in m[1].split(',')]
    if a[0]=='sp':base=r[31]
    elif re.fullmatch(r'x\d+',a[0]):base=r[int(a[0][1:])]
    else:return None
    n=0
    if len(a)>1:
        if a[1].startswith('#'):n=int(a[1][1:],0)
        elif re.fullmatch(r'[wx](?:\d+|zr)',a[1]):
            n=0 if a[1][1:]=='zr' else r[int(a[1][1:])]
            if a[1][0]=='w':n&=0xffffffff
            if len(a)>2:
                mod=re.fullmatch(r'(lsl|uxtw|sxtw|sxtx)(?: #(\d+))?',a[2])
                if not mod:return None
                if mod[1]=='sxtw' and n>=1<<31:n-=1<<32
                n<<=int(mod[2] or 0)
        else:return None
    return (base+n)&((1<<64)-1)
def main(d):
    ins={}
    for line in (d/'sampled-insns.txt').read_text().splitlines():
        pc,name,off,op,*args=line.split();ins[int(pc,16)]=(name,op,' '.join(args))
    syms={}
    for l in (d/'data-symbols.txt').read_text().splitlines():
        a,n,_,name=l.split(maxsplit=3);a=int(a,16);n=int(n,16)
        if n>syms.get(a,(0,''))[0]:syms[a]=n,name
    keys=sorted(syms)
    def symbol(addr):
        j=bisect_right(keys,addr)-1
        if j>=0 and addr<keys[j]+syms[keys[j]][0]:return syms[keys[j]][1]
        return None
    bins=Counter();sites=Counter();byrun=Counter();fields=Counter();ram=Counter();writes=Counter()
    for i in range(1,5):
        s=(d/f'run-{i}.log').read_text();scope=re.findall(r'^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$',s,re.M)
        regs=re.findall(r'^\[OPREG\] (\d+) (\w+) (.*)$',s,re.M)
        assert len(regs)==len(scope)>0
        bases=Counter(int(v.split()[26],16) for _,q,v in regs if ins.get(int(q,16),('',))[0].startswith('ngb_reg_sub_'))
        base,frequency=bases.most_common(1)[0]
        assert base and frequency>sum(bases.values())*.9,(base,frequency,bases)
        for (f,depth,pc),(g,q,raw) in zip(scope,regs):
            assert (f,pc)==(g,q)
            if int(depth):continue
            name,op,args=ins.get(int(pc,16),('','',''))
            if not re.match(r'^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+',name) or not op.startswith(('ld','st')):continue
            if re.search(r'\[(?:x2[6789]|sp)\b',args):continue
            r=[int(x,16) for x in raw.split()];assert len(r)==32
            ea=address(args,r)
            kind=('undecoded' if ea is None else 'guest RAM' if 0<=ea-base<64*1024**2 else 'near native SP' if abs(ea-r[31])<65536 else symbol(ea) or 'other address')
            phase='1-30' if int(f)<=30 else '31-120'
            if kind=='g_regs':
                fields[phase,ea-keys[bisect_right(keys,ea)-1],op[:2]]+=1
            if phase=='31-120' and kind=='g_regs' and op.startswith('st') and 120<=ea-keys[bisect_right(keys,ea)-1]<248:
                writes[int(pc,16),name,ea-keys[bisect_right(keys,ea)-1],op,args]+=1
            if kind=='guest RAM':
                ram[phase,(ea-base)>>20,op[:2]]+=1
            bins[phase,kind,op[:2]]+=1;byrun[i,phase,kind]+=1
            sites[phase,kind,name,op,args]+=1
    print('Indirect base only, D3D depth zero, named guest body; delivered PC samples, not cycles.')
    for key,val in sorted(bins.items()):print(*key,val)
    print('g_regs byte offsets',fields.most_common(32));print('RAM MiB regions',ram.most_common(24))
    with (d/'xmm-sites.txt').open('w') as out:
        for (pc,fn,off,op,args),n in sorted(writes.items()):print(hex(pc),fn,off,n,op,args,file=out)
    print('by run',sorted(byrun.items()));print('most common sites',sites.most_common(12))
if __name__=='__main__':main(Path(sys.argv[1]))
