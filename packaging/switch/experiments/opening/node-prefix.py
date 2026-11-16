"""Record values consumed by the original search, not a second RAM snapshot."""
from pathlib import Path
def transform(s):
 a=s.index('void sub_001CC7E0(void)\n{');b=s.index('\n}',a);t=s[a:b]
 k='    ecx = MEM32(eax + 0xC);';assert t.count(k)==1
 t=t.replace(k,k+'\n    unsigned q=256,i=128; if(np_active){q=np_used++;if(q<256){np_q[q][0]=ecx;np_q[q][1]=ebp;}}')
 k='    if (CMP_AE(_fa, _fb)) goto loc_001CC82E;';assert t.count(k)==1
 t=t.replace(k,'    if(q<256){i=np_q[q][2]++;if(i<128){np_v[q][i][0]=ecx;np_v[q][i][1]=_fa;}}\n'+k)
 k='    ecx = MEM32(ecx + 4);';assert t.count(k)==1
 t=t.replace(k,k+' if(q<256&&i<128)np_v[q][i][2]=ecx;')
 return 'extern unsigned np_active,np_used,np_q[256][3],np_v[256][128][3];\n'+s[:a]+t+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-prefix'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-prefix','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-prefix/recomp_0016.c').unlink()
