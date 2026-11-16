"""Specialize checkpoint calls only when two immediate instructions prove the VA."""
import struct,subprocess
from pathlib import Path
def install(p,regs):
 src=(Path(__file__).resolve().parents[2]/'arm-registers/checkpoint.S').read_text()
 a=src.index('ngb_reg_checkpoint:\n')
 assert all(v & (1<<20) for v in (0x17a010,0x31dc50,0x3cc310))
 # Separate complete routine, preserving unwind info on both entry paths.
 copy=src[a:].replace('ngb_reg_checkpoint','ngb_literal_checkpoint').replace('.L','.Llit')
 copy=copy.replace('ngb_literal_checkpoint:\n','ngb_literal_checkpoint:\n tbnz w0,#20,ngb_reg_checkpoint\n',1)
 copy=copy[:copy.index('\tmov\tw3, 40976')]+copy[copy.index('\tadrp\tx3, ngb_reg_current_va'):]
 f=p.out/'entry-literal.S';f.write_text(src+'\n.text\n.p2align 4\n.global ngb_literal_checkpoint\n.type ngb_literal_checkpoint,%function\n'+copy)
 obj=f.with_suffix('.o');subprocess.run(['cc','-c',f,'-o',obj],check=True)
 p.link[p.link.index(str(regs/'checkpoint.o'))]=str(obj)
def patch(f):
 nm=subprocess.check_output(['nm','-nS','--defined-only',f],text=True)
 names={};guest=[]
 for row in nm.splitlines():
  x=row.split()
  if len(x)!=4:continue
  addr,size,t,n=x
  if n in ('ngb_reg_checkpoint','ngb_literal_checkpoint'):names[n]=int(addr,16)
  if n.startswith(('ngb_reg_sub_','ngb_reg_d3d_orig_')):guest.append((int(addr,16),int(size,16)))
 old=names['ngb_reg_checkpoint'];new=names['ngb_literal_checkpoint'];n=0
 import mmap
 with f.open('r+b') as h,mmap.mmap(h.fileno(),0) as buf:
  u=lambda fmt,o:struct.unpack_from('<'+fmt,buf,o)
  ph=[u('IIQQQQQQ',u('Q',32)[0]+i*u('H',54)[0]) for i in range(u('H',56)[0])]
  seg,=[v for v in ph if v[0]==1 and v[1]&1 and v[3]<=old<v[3]+v[5]]
  for a,size in guest:
   assert seg[3]<=a<=a+size<=seg[3]+seg[5]
   start=a-seg[3]+seg[2]
   for j in range(8,size,4):
    pc=a+j; off=start+j
    ins=u('I',off)[0]
    if ins != (0x94000000|(((old-pc)//4)&0x3ffffff)):continue
    end=off
    if u('I',end-4)[0]==0x910003fd:end-=4
    if end<start+8:continue
    z,k=u('II',end-8)
    if z&0xffe0001f!=0x52800000 or k&0xffe0001f!=0x72a00000:continue
    va=((z>>5)&65535)|(((k>>5)&65535)<<16)
    if va & (1<<20):continue
    # Only entry straight-line code. No alternate path may enter after either MOV.
    # Entry prologue: whitelist only frame saves, frame setup, immediate moves.
    if j>64:continue
    words=u('I'*(j//4),start)
    if any((w>>26 in (5,37)) or ((w&0xff000000) in (0x54000000,0xd6000000)) or ((w&0x7e000000) in (0x34000000,0x36000000)) for w in words):continue
    if not -(1<<27)<=new-pc<(1<<27):raise ValueError('BL range')
    struct.pack_into('<I',buf,off,0x94000000|(((new-pc)//4)&0x3ffffff));n+=1
 print('specialized literal entry sites',n,flush=True);assert n>100
