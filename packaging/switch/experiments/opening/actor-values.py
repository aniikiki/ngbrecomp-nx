"""Count actor table roots and indices across both passes, without extra guest reads."""
from pathlib import Path
def transform(s):
 for i,(va,root,sel,last) in enumerate([('001CC430','ebx','ecx','eax = MEM32(edx + eax + 8);'),('001CC6E0','edi','ebp','eax = MEM32(ecx + eax + 8);')]):
    a=s.index('loc_'+va+': ;');b=s.index(last,a)+len(last);body=s[a:b]
    k='eax = MEM32('+root+' + 0x26DC);';assert body.count(k)==1
    body=body.replace(k,k+' unsigned av_ptr=eax;').replace('eax = MEM32(eax);','eax = MEM32(eax); unsigned av_base=eax;')
    body=body.replace(': ;',': ; unsigned av_root='+root+',av_idx=eax; unsigned long long av_start=av_begin('+str(i)+');',1)
    body+=f' if(av_on)av_end({i},av_start,av_root,av_idx,{sel},esi,av_ptr,av_base,eax);'
    s=s[:a]+body+s[b:]
 return 'extern unsigned av_on;extern unsigned long long av_begin(unsigned);extern void av_end(unsigned,unsigned long long,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);\n'+s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-actor-values'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'actor-values','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-actor-values/recomp_0016.c').unlink()
