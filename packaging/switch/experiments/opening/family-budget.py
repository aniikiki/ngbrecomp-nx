"""Sample each of three search bodies separately; stop before dispatch."""
from pathlib import Path
def transform(s):
 for i,(fn,start,loop,exits) in enumerate((
  ('001CBED0','esi = MEM32(ecx + 0xC);','001CBF20',['001CBF2E','001CBF30']),
  ('001CC4D0','edx = MEM32(eax + 0xC);','001CC510',['001CC594','001CC51C']),
  ('001CC7E0','ecx = MEM32(eax + 0xC);','001CC7F8',['001CC82E','001CC804']))):
  a=s.index('void sub_'+fn+'(void)\n{');b=s.index('\n}',a)
  t=s[a:b].replace('\n{','\n{ unsigned long long fb_tick=0; unsigned fb_frame=0;',1)
  j=t.rindex(start,0,t.index('loc_'+loop+': ;'))+len(start)
  t=t[:j]+f" fb_frame=fb_window;if(fb_frame){{fb_counts[{i}][0]++;fb_rng=1664525u*fb_rng+1013904223u;unsigned m=fb_rng>>29;if(!m)fb_tick=fb_clock();else if(m==1){{unsigned long long t0=fb_clock();fb_ns[{i}][1]+=fb_clock()-t0;fb_counts[{i}][2]++;}}}}"+t[j:]
  for label in exits:
   k='loc_'+label+': ;';assert t.count(k)==1
   t=t.replace(k,k+f" if(fb_tick){{if(fb_frame==fb_window){{fb_ns[{i}][0]+=fb_clock()-fb_tick;fb_counts[{i}][1]++;}}fb_tick=0;}}")
  s=s[:a]+t+s[b:]
 return 'extern unsigned fb_window,fb_rng,fb_counts[3][3];extern unsigned long long fb_ns[3][2],fb_clock(void);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-family-budget'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'family-budget','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-family-budget/recomp_0016.c').unlink()
