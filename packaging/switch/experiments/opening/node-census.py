"""Count original searches and actual visits without reading extra guest memory."""
from pathlib import Path
def transform(s):
 a=s.index('void sub_001CC7E0(void)\n{');b=s.index('\n}',a)
 part=s[a:b]
 k='    ecx = MEM32(eax + 0xC);';assert part.count(k)==1
 part=part.replace(k,k+"""
    if(nc_active){
        unsigned h=((ecx>>4)^(ebp*2654435761u))&4095;
        nc_counts[0]++; if (!ecx) nc_counts[1]++;
        if(nc_tab[h][0] && nc_tab[h][1]==ecx && nc_tab[h][2]==ebp) nc_counts[2]++;
        nc_tab[h][0]=1;nc_tab[h][1]=ecx;nc_tab[h][2]=ebp;
    }""")
 for i,loc in enumerate(('001CC7F8','001CC7FD','001CC830'),3):
    k='loc_'+loc+': ;';assert part.count(k)==1
    part=part.replace(k,k+f' if(nc_active)nc_counts[{i}]++;')
 return 'extern unsigned nc_active,nc_tab[4096][3],nc_counts[6];\n'+s[:a]+part+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-census'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-census','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-census/recomp_0016.c').unlink()
