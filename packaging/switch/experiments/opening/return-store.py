"""Fuse masked offset and RAM base at the return-PC store; retain the checked miss."""
from pathlib import Path
import re
def transform(s):
 pattern=r'PUSH32\(esp, (0x[0-9A-F]+u)\);(?= RECOMP_ABI_CALL\()'
 def change(m):
  return ("do { esp-=4u; uint32_t rs_a=esp, rs_v="+m[1]+"; "
          "if(__builtin_expect(rs_a<reg_ends[rs_a>>12],1)){"
          "__asm__ volatile(\"str %w0,[%1,%w2,uxtw]\" :: \"r\"(rs_v),\"r\"(ngb_fast_ram),\"r\"(rs_a&0x7fffffffu):\"memory\");"
          "}else *(volatile uint32_t*)ngb_guest_scalar_fallback(rs_a,4)=rs_v; }while(0);")
 s,n=re.subn(pattern,change,s);assert n;print("return stores",n,flush=True);return s
if __name__=='__main__':
    p=Path(__file__).parent
    s=(p/'page-hot-o3.py').read_text().replace("compact='--compact-loops' in sys.argv","compact=True").replace("d=d.parent/'opening-compact-loops'","d=d.parent/'opening-return-store'")
    k='exec(compile(s,\'page-o3\',\'exec\'),{})'
    a=s.index('names=[');b=s.index('\n',a);s=s[:a]+"names=['recomp_%04d.c'%u for u in (2,10,16,26,39)]"+s[b:]
    s=s.replace(k,"""for name in names:
 (d/name).write_text(transform((base/'gen'/name).read_text()))
k=' sp.run(c,cwd=w,check=True)'
s=s.replace(k," c.insert(-1,'-I/work/build/switch-runtime/gen');c[-1]=str(o/n)\\n"+k)
"""+k)
    exec(compile(s,'return-store','exec'),{'transform':transform})
    for f in Path('build/switch-runtime/core-perf/opening-return-store').glob('recomp_*.c'):f.unlink()
