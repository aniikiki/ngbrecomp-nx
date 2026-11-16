"""Independently sample parent body or direct call sites; never time both in one invocation."""
from pathlib import Path
import re
def transform(s):
 a=s.index('loc_0013ED30: ;');b=s.index('\n}',a);body=s[a:b]
 k='loc_0013ED30: ;';body=body.replace(k,k+' unsigned ap_frame=ap_epoch; unsigned long long ap_t=ap_begin(0);')
 k='esp += 4; return;';assert body.count(k)==4
 body=body.replace(k,'esp += 4; if(ap_t)ap_end(0,ap_frame,ap_t); return;')
 pat=r'RECOMP_ABI_CALL\(0x[0-9A-F]+u, sub_[0-9A-F]+\);'
 assert len(re.findall(pat,body))==12
 i=iter(range(1,13))
 def wrap(m):
    n=next(i);return f'{{unsigned f=ap_epoch; unsigned long long t=0; if(!ap_t)t=ap_begin({n}); '+m[0]+f' if(t)ap_end({n},f,t);}}'
 body=re.sub(pat,wrap,body)
 return 'extern unsigned ap_epoch;extern unsigned long long ap_begin(unsigned);extern void ap_end(unsigned,unsigned,unsigned long long);\n'+s[:a]+body+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-axis-parent'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0010.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'axis-parent','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-axis-parent/recomp_0010.c').unlink()
