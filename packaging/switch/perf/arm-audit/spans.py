import hashlib,struct as S,sys,re,collections,gzip
from pathlib import Path
d=Path('/audit');root=Path('build/switch-runtime');p=root/'history/0.56.23'
manifest=(p/'linked-inputs.txt').read_text().splitlines()
for l in manifest:
 h,n=l.split();assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
b=(d/'linked.elf').read_bytes();nro=(p/'ngb-startup.nro').read_bytes()
_,_,arch,_,_,_,off,_,_,_,_,ent,num,shstr=S.unpack_from('<16sHHIQQQIHHHHHH',b)
assert arch==183
secs=[S.unpack_from('<IIQQQQIIQQ',b,off+ent*i) for i in range(num)]
def st(tab,n):return tab[n:tab.index(b'\0',n)].decode(errors='replace')
def dat(s):return b[s[4]:s[4]+s[5]]
def name(i):return st(dat(secs[shstr]),secs[i][0])
mapping={}
for s in secs:
 if s[1]!=2:continue
 tab=dat(secs[s[6]])
 for no,info,other,idx,val,size in S.iter_unpack('<IBBHQQ',dat(s)):
  if idx>=num or not secs[idx][2]&4:continue
  if tab[no:no+2] in (b'$x',b'$d') and tab[no+2] in (0,46):
   mapping[idx,val]=tab[no+1:no+2]==b'x'
textsize=S.unpack_from('<I',nro,36)[0]; mask=bytearray(textsize//4);totalbits=0
for i,s in enumerate(secs):
 if not s[2]&4 or not s[5]:continue
 a,z=s[3],s[3]+s[5]; m=sorted((k[1],v) for k,v in mapping.items() if k[0]==i)
 for j,(lo,x) in enumerate(m):
  hi=m[j+1][0] if j+1<len(m) else z
  if x:
   assert not lo%4 and not hi%4 and hi<=textsize
   mask[lo//4:hi//4]=b'\1'*((hi-lo)//4)
(d/'mask').write_bytes(mask)
rows={};start=False;sec=''
for l in (d/'linked.map').read_text().splitlines():
 if l.startswith('.text '):start=True
 if start and l.startswith('.init '):break
 if not start:continue
 m=re.match(r'^ (\.\S+)(?:\s|$)',l)
 if m:sec=m[1]
 m=re.match(r'^\s+(?:\.\S+\s+)?(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S+)$',l)
 if not m:continue
 lo,size=int(m[1],16),int(m[2],16);file=m[3].split('/')[-1]
 unit=re.fullmatch(r'(?:retained-)?recomp_(\d{4})\.c\.o',file)
 glue=file in ('entry.o','gates.o','checkpoint.o','gameplay.o') or sec.startswith('.text.ngbs_sub_')
 if not size or not (glue or unit):continue
 group=unit[1] if unit else 'glue'
 assert size%4==lo%4==0,(sec,size,lo)
 assert lo not in rows,(sec,lo)
 assert b[secs[1][4]+lo:secs[1][4]+lo+size]==nro[lo:lo+size],(sec,lo,'published text mismatch')
 rows[lo]=size,group,sec
assert {g for n,g,s in rows.values() if g!='glue'}=={f'{i:04}' for i in range(47)}
with (d/'spans').open('w') as f:
 for lo,(sz,g,sec) in sorted(rows.items()):print(lo,sz,g,sec,file=f)
print('Verified linked bytes,',len(rows),'ranges;',sum(sz for sz,g,s in rows.values()),'bytes',flush=True)
