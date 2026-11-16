from pathlib import Path
def transform(s):
 a=s.index('static inline bool ngb_arm_x87_row');b=s.index('/* Transform three',a)
 t=s[a:b]
 assert t.count('return false;')==4 and t.count('return true;')==1
 for n in range(4):
  t=t.replace('return false;',f'return rr_exit({n},column);',1)
 t=t.replace('return true;', 'return rr_exit(4+!!(g_fp_control_word&0x300u),column);')
 return s[:a]+"""extern unsigned rr_on,rr_counts[2][6];
static inline bool rr_exit(unsigned why, bool col){if(rr_on)rr_counts[col][why]++;return why>=4;}
"""+t+s[b:]
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-row-reasons'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (39,)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text((base/'gen'/name).read_text())
 (d/'arm_math.h').write_text(transform(Path('packaging/switch/runtime/arm_math.h').read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'row-reasons','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-row-reasons').glob('recomp_*.c'):f.unlink()
