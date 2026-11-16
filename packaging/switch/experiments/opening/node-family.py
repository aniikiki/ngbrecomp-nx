"""Observe whether three searches actually traverse the same path, without extra guest reads."""
from pathlib import Path
def transform(s):
 for family,(fn,head,key,start,loop) in enumerate((
  ('001CBED0','esi','ebx','esi = MEM32(ecx + 0xC);','001CBF20'),
  ('001CC4D0','edx','edi','edx = MEM32(eax + 0xC);','001CC510'),
  ('001CC7E0','ecx','ebp','ecx = MEM32(eax + 0xC);','001CC7F8'))):
  a=s.index('void sub_'+fn+'(void)\n{'); b=s.index('\n}',a)
  part=s[a:b]
  k='loc_'+loop+': ; ngb_guest_block_poll();'
  assert part.count(k)==1
  j=part.rindex(start,0,part.index(k))+len(start)
  part=part[:j]+f" unsigned fs=1024;if(nf_active){{fs=nf_used++;if(fs<1024){{nf_rows[fs][0]={family};nf_rows[fs][1]={head};nf_rows[fs][2]={key};}}}}"+part[j:]
  j=part.index('\n',part.index('_fb =',part.index(k)))
  part=part[:j]+f" if(fs<1024){{nf_rows[fs][3]++;nf_rows[fs][4]=nf_rows[fs][4]*16777619u^{head};nf_rows[fs][5]=nf_rows[fs][5]*16777619u^_fa;}}"+part[j:]
  s=s[:a]+part+s[b:]
 return 'extern unsigned nf_active,nf_used,nf_rows[1024][6];\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-family'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-family','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-family/recomp_0016.c').unlink()
