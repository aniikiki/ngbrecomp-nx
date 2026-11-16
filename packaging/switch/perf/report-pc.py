"""Report the sampled native instruction and routine from the *same* host ELF.
Run inside the Linux ARM build container; no external Python dependencies."""
import bisect
import collections
from pathlib import Path
import re
import subprocess
import sys

binary, log = sys.argv[1:3]
rows = subprocess.check_output(['nm','-n','-S',binary], text=True).splitlines()
base = int(next(row.split()[0] for row in rows if row.endswith(' __executable_start')),16)
symbols = []
for line in rows:
    m = re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) [tTwW] (.+)',line)
    if m and int(m[2],16):
        symbols.append((int(m[1],16),int(m[2],16),m[3]))
symbols.sort()
starts = [s[0] for s in symbols]
logtext=Path(log).read_text()
runtime_base=re.search(r'^\[ARMBASE\] ([0-9a-f]+)$',logtext,re.M)
images=[(int(a,16),int(b,16),int(off,16),path.strip()) for a,b,off,path in re.findall(
    r'^\[ARMMAP\] ([0-9a-f]+)-([0-9a-f]+) ..x. ([0-9a-f]+) \S+ \d+\s+([^\n]+)$',logtext,re.M)]
libraries={}
def external(pc):
    if runtime_base:
        addr=(pc-base+int(runtime_base[1],16)) % (1<<64)
        for low,high,offset,path in images:
            if low<=addr<high:
                lib=Path(path)
                pos=addr-low+offset
                if path not in libraries:
                    dynamic=[]
                    if lib.is_file():
                        nm=subprocess.run(['nm','-D','-n','-S','--defined-only',path],text=True,capture_output=True)
                        for row in nm.stdout.splitlines():
                            m=re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) [tTwWiI] (.+)',row)
                            if m: dynamic.append((int(m[1],16),int(m[2],16),m[3]))
                    dynamic.sort()
                    libraries[path]=([x[0] for x in dynamic], dynamic)
                keys,syms=libraries[path]
                idx=bisect.bisect_right(keys,pos)-1
                sym=syms[idx][2] if idx>=0 and pos<syms[idx][0]+syms[idx][1] else '(private)'
                return lib.name+':'+sym
    return 'outside sized executable symbols'
hits = collections.Counter()
pcs = collections.Counter(int(p,16)+base for p in re.findall(r'^\[ARMPC\] ([0-9a-f]+)$',Path(log).read_text(),re.M))
if not pcs:
    sys.exit('no PC samples')
for pc,n in pcs.items():
    i=bisect.bisect_right(starts,pc)-1
    hits[symbols[i][2] if i>=0 and pc<starts[i]+symbols[i][1] else external(pc)]+=n
total=sum(hits.values())
print(f'{total} guest-thread PC samples, scene flips 1681..1920')
for name,n in hits.most_common(25):
    print(f'{100*n/total:5.1f}% {n:5} {name}')
print('Most frequent individually sampled instructions:')
for pc,n in sorted(((pc,n) for pc,n in pcs.items() if starts[0]<=pc<=starts[-1]),key=lambda item:-item[1])[:16]:
    out=subprocess.check_output(['objdump','-d',f'--start-address={pc}',f'--stop-address={pc+4}',binary],text=True)
    print(n,out.strip().splitlines()[-1].strip())
