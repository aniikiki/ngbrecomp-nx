"""Whitelist adjacent generated C statements with a single base and one MEM32 each."""
from pathlib import Path
import re
def access(line):
    reg=r'e(?:ax|bx|cx|dx|si|di|bp|sp)'
    mem=rf'MEM32\(({reg})(?: \+ (0x[0-9a-fA-F]+|\d+))?\)'
    m=re.fullmatch(rf'({reg}) = '+mem+r';',line)
    if m:return m[2],int(m[3] or '0',0),m[1]
    m=re.fullmatch(mem+rf' = ({reg});',line)
    if m:return m[1],int(m[2] or '0',0),None
    return None
def main():
    # Reuse the checked GCC expansion and source-location accounting of the original probe.
    p=Path(__file__).with_name('word-site-owners.py');s=p.read_text()
    s=s.replace('     matched.add(key);','     locations[key]=(owner,pos,lines[pos-1].strip());matched.add(key);')
    s=s[:s.index('for c in (kinds,owners,ops):')]
    ns={'__file__':str(p),'locations':{}};exec(compile(s,str(p),'exec'),ns)
    loc=ns['locations'];index={(u,owner,pos):i for (u,i),(owner,pos,_) in loc.items()}
    d=ns['d'].parent/'opening-word-runs';d.mkdir(exist_ok=True)
    with (d/'eligible.inc').open('w') as f,(d/'sites.txt').open('w') as g:
        for (u,i),(owner,pos,line) in sorted(loc.items()):
            j=index.get((u,owner,pos-1));b=access(line)
            if j is None or b is None:continue
            a=access(loc[u,j][2])
            if not a or a[0]!=b[0] or a[2]==a[0] or abs(a[1]-b[1])>4092:continue
            print(f'[{u}][{i}]={{{j+1},{b[1]-a[1]}}},',file=f)
            print(u,i,j,owner,loc[u,j][2],line,file=g)
if __name__=='__main__':main()
