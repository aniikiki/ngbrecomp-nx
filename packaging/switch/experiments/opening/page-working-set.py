"""Cross-check the spatial concentration of sampled page-bound loads in the opening."""
from collections import Counter
from pathlib import Path
from runpy import run_path
import re

d = Path("build/switch-runtime/core-perf/opening-outside-operand")
address = run_path(str(Path(__file__).with_name("outside-operand-report.py")))["address"]
base, size = next((int(a,16), int(n,16)) for a,n,_,sym in
                  (l.split(maxsplit=3) for l in (d/"data-symbols.txt").read_text().splitlines())
                  if sym == "opening_end4")
ins = {int(pc,16): (name, op, " ".join(args)) for pc,name,off,op,*args in
       (l.split() for l in (d/"sampled-insns.txt").read_text().splitlines())}
for start, stop in ((1,30),(31,120)):
    window = [Counter(), Counter()]
    esp = [Counter(), Counter()]
    phases = [(Counter(), Counter(), Counter()) for _ in range(2)]
    for i in range(1,5):
        s = (d/f"run-{i}.log").read_text()
        assert "verified 120 original demo frames" in s
        sc = re.findall(r"^\[D3D_SCOPE_PC\] (\d+) (\d+) (\w+)$",s,re.M)
        rs = re.findall(r"^\[OPREG\] (\d+) (\w+) (.*)$",s,re.M)
        assert len(sc) == len(rs) > 0
        lines, pages, sites = phases[(i-1)//2]
        for (f,depth,pc),(g,q,raw) in zip(sc,rs):
            assert (f,pc) == (g,q)
            if int(depth) or not start<=int(f)<=stop: continue
            name,op,args = ins.get(int(pc,16),("","",""))
            if not (re.match(r"^(?:ngb_reg_)?(?:sub_|d3d_orig_)[0-9A-F]+",name)
                    and op=="ldr" and re.search(r"\[x27(?:,|\])",args)): continue
            regs=[int(x,16) for x in raw.split()]
            ea=address(args,regs)
            assert regs[27]==base and base<=ea<base+size and (ea-base)%4==0
            lines[ea//64]+=1
            pages[(ea-base)//4]+=1
            sites[pc]+=1
            va=((ea-base)//4)<<12
            dist=abs((va>>12)-((regs[22]&0xffffffff)>>12))
            esp[(i-1)//2]["same" if dist == 0 else "adjacent" if dist == 1 else "other"]+=1
            if 0x01180000 <= va < 0x011e9000:
                window[(i-1)//2]["in known stack window"]+=1
            else:
                window[(i-1)//2]["outside known stack window"]+=1
    for label, a, b in zip(("64-byte lines","guest pages","instruction PCs"),*phases):
        print(start,stop,label,"samples",sum(a.values()),sum(b.values()),"distinct",len(a),len(b),
              "holdout hits on training top 1/4/8/all",
              [sum(b[k] for k,_ in a.most_common(n)) for n in (1,4,8,None)])
    print("distance to live guest ESP page:",esp)
    print("fixed window (all scalar load sites):",window)
    a,b = phases[0][1],phases[1][1]
    print("training hot guest page starts (VA,hits,holdout)",
          [(hex(k<<12),v,b[k]) for k,v in a.most_common(6)])
