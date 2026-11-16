"""Trace completed searches on selected flips without extra guest reads."""
from pathlib import Path
def transform(s):
 a=s.index('void sub_001CC7E0(void)\n{');b=s.index('\n}',a)
 t=s[a:b];k='    ecx = MEM32(eax + 0xC);';assert t.count(k)==1
 t=t.replace(k,k+'\n    unsigned no_slot=256; if(no_active){no_slot=no_used++;if(no_slot<256){no_rows[no_slot][0]=ecx;no_rows[no_slot][1]=ebp;}}')
 for k,stmt in [('loc_001CC7F8: ;','no_rows[no_slot][2]++'),('loc_001CC830: ;','no_rows[no_slot][3]=ecx')]:
    assert t.count(k)==1;t=t.replace(k,k+' if(no_slot<256){'+stmt+';}')
 return 'extern unsigned no_active,no_used,no_rows[256][4];\n'+s[:a]+t+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-node-order'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_0016.c']"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'node-order','exec'),{'transform':transform})
    Path('build/switch-runtime/core-perf/opening-node-order/recomp_0016.c').unlink()
