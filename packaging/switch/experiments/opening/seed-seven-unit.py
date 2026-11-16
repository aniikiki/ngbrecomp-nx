"""Install the same seed setter in both host arms, preserving the old 14-unit register ABI."""
import subprocess
def install(p,regs):
 n='recomp_0037.c'
 s=(regs/(n+'.gated.s')).read_text()
 a=s.index('\nngb_reg_sub_0036E134:\n');b=s.index('\n\t.size\tngb_reg_sub_0036E134,',a)
 body=s[a:b];k='\tstr\tw20, [x0]'
 assert body.count(k)==1 and body.count('\tldr\tw20, [x0]')==1
 body=body.replace(k,'\tstr x9,[sp,#-16]!\n\tmov w9,#7\n\tstr w9,[x0]\n\tldr x9,[sp],#16')
 f=p.out/'seed-seven.s';obj=f.with_suffix('.o')
 try:
  f.write_text(s[:a]+body+s[b:])
  subprocess.run(['cc','-c','-march=armv8-a+crc+crypto',f,'-o',obj],check=True)
 finally:f.unlink(missing_ok=True)
 p.link[p.link.index(str(regs/(n+'.o')))]=str(obj)
