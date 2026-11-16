"""Patch five verified comparison sites in the temporary host replay only."""
import struct,subprocess,re,sys
from pathlib import Path
sites=[('001BB990',0x250,8,12),('003433F0',0xc14,44,20),('003433F0',0xc34,20,76),('0013BB10',0x2d8,16,68),('0018B5F0',0x3a78,64,84)]
def driver(src):
 k='void angle_boundary(unsigned f, unsigned draws) {'
 assert src.count(k)==1
 code='unsigned long long stk_count[5][3];\n'
 for i,(_,_,d0,d1) in enumerate(sites):
  # Normal registers/flags restored; count the first guard passing and whether
  # both four-byte spans fit a single page. No write to the guest stack.
  asm=f""".pushsection .text
.global stk_stub{i}
stk_stub{i}:
stp x9,x10,[sp,#-16]!
adrp x9, stk_count
add x9,x9,:lo12:stk_count
add x9,x9,#{24*i}
ldr x10,[x9]
add x10,x10,#1
str x10,[x9]
ldp x9,x10,[sp],#16
.global stk_cmp{i}
stk_cmp{i}: nop
.global stk_fail{i}
stk_fail{i}: nop
stp x9,x10,[sp,#-16]!
adrp x9,stk_count
add x9,x9,:lo12:stk_count
add x9,x9,#{24*i}
ldr x10,[x9,#8]
add x10,x10,#1
str x10,[x9,#8]
add w10,w22,#{min(d0,d1)}
and w10,w10,#4095
add w10,w10,#{max(d0,d1)-min(d0,d1)+3}
tbnz w10,#12,1f
ldr x10,[x9,#16]
add x10,x10,#1
str x10,[x9,#16]
1: ldp x9,x10,[sp],#16
.global stk_back{i}
stk_back{i}: nop
.popsection"""
  code+='__asm__("'+asm.replace('\n','\\n')+'");\n'
 return src.replace(k,code+k+'''if(f==0||f==30||f==120){for(unsigned i=0;i<5;i++){if(f)fprintf(stderr,"[STK_PAIR] %u %u %llu %llu %llu\\n",f,i,stk_count[i][0],stk_count[i][1],stk_count[i][2]);for(unsigned j=0;j<3;j++)stk_count[i][j]=0;}}''')
def patch(p):
 syms={r[2]:int(r[0],16) for l in subprocess.check_output(['nm','-n',p],text=True).splitlines() if len(r:=l.split())==3}
 with p.open('r+b') as f:
  h=f.read(64);assert h[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',h,18)[0]==183
  f.seek(struct.unpack_from('<Q',h,32)[0]);seg=[struct.unpack('<II6Q',f.read(56)) for _ in range(struct.unpack_from('<H',h,56)[0])]
  def pos(pc):
   v,=[t[2]+pc-t[3] for t in seg if t[0]==1 and t[1]&1 and t[3]<=pc<=t[3]+t[5]-4];f.seek(v)
  def word(pc):pos(pc);return int.from_bytes(f.read(4),'little')
  def put(pc,w):pos(pc);f.write(struct.pack('<I',w))
  def branch(a,b):
   n=(b-a)//4;assert -(1<<25)<=n<1<<25;return 0x14000000|(n&0x3ffffff)
  for i,(fn,o,*_) in enumerate(sites):
   a=syms['ngb_reg_sub_'+fn]+o;c=a+4
   assert word(a)==0xb8617b61
   cmp=word(c);bc=word(c+4);assert cmp&0xffe0fc1f==0x6b00001f and bc&0xff00001f in (0x54000002,0x54000009)
   start,test,fail,back=[syms[x+str(i)] for x in ('stk_stub','stk_cmp','stk_fail','stk_back')]
   assert all(word(x)==0xd503201f for x in (test,fail,back))
   put(test,cmp);put(fail,0x54000000|(((back-fail)//4)<<5)|(bc&15));put(back,branch(back,c+4));put(c,branch(c,start))
