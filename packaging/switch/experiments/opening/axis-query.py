"""Measure executed axis stages and sampled body time in the original 13F960 query."""
from pathlib import Path
def transform(s):
 a=s.index('loc_0013F960: ;');b=s.index('\n}',a);body=s[a:b]
 marks=['0013F960','0013F9A9','0013F9D9','0013FA0F','0013FEC5']
 for i,m in enumerate(marks):
    k='loc_'+m+': ;';assert body.count(k)==1
    v='unsigned aq_f=aq_epoch; unsigned long long aq_t=aq_begin();' if i==0 else f'if(aq_epoch<120)aq_counts[{i}]++;'
    body=body.replace(k,k+' '+v)
 k='esp += 4; return;';assert body.count(k)==6
 body=body.replace(k,'esp += 4; if(aq_t)aq_end(aq_f,aq_t); return;')
 return 'extern unsigned aq_epoch,aq_counts[5];extern unsigned long long aq_begin(void);extern void aq_end(unsigned,unsigned long long);\n'+s[:a]+body+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-axis-query'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0010.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'axis-query','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-axis-query/recomp_0010.c').unlink()
