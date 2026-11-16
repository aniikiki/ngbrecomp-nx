"""Lower-bound audit of repeated ordinary image reads within a precise GCC block."""
from collections import Counter
import re
def inspect(source,unit,counts,sites):
    def clear():
        return {'x26':0}, set()
    addr,seen=clear();weight=0;fn=''
    for l in source:
        if m:=re.fullmatch(r'(\w+):\s*',l):
            fn=m[1];weight=0
        if m:=re.match(r'// BLOCK \d+, count:(\d+)(.*?) seq:',l):
            weight=int(m[1]) if m[2].strip() in ('','(precise)') else 0
            addr,seen=clear();continue
        # GCC can place the basic-block label after its count.
        if re.match(r'^\.L\w+:',l):
            addr,seen=clear();continue
        if not weight or not fn:continue
        m=re.match(r'^\s+([a-z][a-z.0-9]*)\s+(.*?)\s*$',l)
        if not m:continue
        op,args=m.groups();args=args.split('//')[0].strip()
        if op in ('bl','blr','b','br','ret') or op.startswith(('cb','tb','b.','st','cas','swp','ldadd','dmb','dsb','isb','svc')):
            addr,seen=clear();continue
        rv=None
        if m:=re.fullmatch(r'x\d+,\s*(x\d+),\s*#?(0x[\da-f]+|\d+)(?:,\s*lsl\s*#?(12))?',args):
            if op=='add' and m[1] in addr:rv=addr[m[1]]+(int(m[2],0)<<(12 if m[3] else 0))
        if op=='mov' and (m:=re.fullmatch(r'x\d+,\s*(x\d+)',args)):rv=addr.get(m[1])
        if op in ('ldr','ldur','ldrb','ldrh') and (m:=re.fullmatch(r'([wsxdq])\d+,\s*\[(x\d+)(?:,\s*#?(-?(?:0x[\da-f]+|\d+)))?\]',args)) and m[2] in addr:
            width=1 if op=='ldrb' else 2 if op=='ldrh' else dict(w=4,s=4,x=8,d=8,q=16)[m[1]]
            va=addr[m[2]]+int(m[3] or 0,0) if m[3] else addr[m[2]]
            if 0x8000<=va<=0x1000000-width:
                counts[unit,'recognized']+=weight
                if (va,width) in seen:counts[unit,'repeat']+=weight;sites[fn,va,width]+=weight
                seen.add((va,width))
        # Forget integer destinations, including the second result of pair loads.
        for i,arg in enumerate(args.split(',')[:2 if op.startswith('ldp') else 1]):
            if m:=re.fullmatch(r'[wx](\d+)',arg.strip()):addr.pop('x'+m[1],None)
        if '!' in args or '],' in args:addr,seen=clear()
        elif rv is not None:addr[args.split(',')[0]]=rv
if __name__=='__main__':
    from pathlib import Path
    p=Path(__file__).with_name('retained-call-work.py');s=p.read_text()
    a=s.index('   fn=None;');b=s.index('  finally:',a)
    s=s[:a]+"   with out.open() as af:inspect(af,u,counts,sites)\n"+s[b:s.index("print('unit caller")]
    s=s.replace("'-fno-reorder-blocks-and-partition'","'-freorder-blocks-and-partition'")
    counts=Counter();sites=Counter()
    exec(compile(s,str(p),'exec'))
    for u in (2,10,16,28,29):print(u,counts[u,'recognized'],counts[u,'repeat'],flush=True)
    print('Leading repeated ordinary image addresses',sites.most_common(20))
