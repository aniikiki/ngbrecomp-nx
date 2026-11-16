"""Assert matched function addresses and unchanged placement of all other BSS objects."""
import sys,subprocess,re
def sy(p):
 rows={}
 for l in subprocess.check_output(['nm','-S',p],text=True).splitlines():
  m=re.fullmatch(r'(\w+) (\w+) ([tTbB]) (.+)',l)
  if m:rows.setdefault((m[3],m[4]),[]).append((int(m[1],16),int(m[2],16)))
 return rows
a,b=map(sy,sys.argv[1:])
k=('B','g_regs')
x,n=a.pop(k)[0];y,m=b.pop(k)[0]
assert (x%64,y-x,n,m)==(0,8,312,312) and a==b
print('identical other text/BSS symbol addresses; g_regs:',hex(x),hex(y),flush=True)
