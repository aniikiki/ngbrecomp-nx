"""Run the real complete loop over precisely the candidates retired by a group.
Restore its initial state after trial and compare at the FINAL candidate's
return, including all transient stack bytes and every affected actor."""
from pathlib import Path
import shlex,subprocess as sp,sys
base=Path('/work/build/switch-runtime');d=base/('opt050/contact-compact' if '--compact' in sys.argv else 'opt050/contact-batch');w=base/'switch'
s=(d/'fast.c').read_text();k='void sub_0013D330(void)\n{'
s=s.replace(k,k+'''
 extern void leaf_log(const char*,...);
 static unsigned calls,ok,groups[16];
 unsigned remain=0,sp_save,group_size,addresses[16],pc,wrd,rc[32];uint64_t ticks,entry;RecompRegs reg;
 uint8_t st[400],mat[64],endw[16][4];
''')
k=' if(contact_group(ebp) || contact_leaf(ebp))goto loc_0013D550;'
s=s.replace(k,'''
 if(!remain && ++calls%11==0 && ebx>=0x7a79c6 && ebx+8*15<0x7a9000 && esp>0x1001000 && esp<0x3dfe000 && ngb_ram_span(esp-256,400)){
  unsigned addr0=ebx;sp_save=esp;
  RecompRegs r0=g_regs;uint32_t rcs[32],pc0=ngb_reg_current_va,w0=MEM32(0xdb67c0);
  uint64_t t0=ngb_guest_polls,e0=ngb_reg_entries;
  uint8_t st0[400],m0[64],vs0[16][4];memcpy(rcs,ngb_reg_recent,128);
  memcpy(st0,ngb_fast_ram+esp-256,400);memcpy(m0,ngb_fast_ram+0x950180,64);
  for(unsigned j=0;j<16;j++){addresses[j]=0x4b4e50+MEM8(addr0+j*8)*0x2800u+0x8cc;memcpy(vs0[j],ngb_fast_ram+addresses[j],4);}
  unsigned n=contact_group(ebp);if(n>=16)__builtin_trap();
  if(n){
   group_size=remain=n;reg=g_regs;memcpy(st,ngb_fast_ram+sp_save-256,400);memcpy(mat,ngb_fast_ram+0x950180,64);
   for(unsigned j=0;j<n;j++)memcpy(endw[j],ngb_fast_ram+addresses[j],4);
   memcpy(rc,ngb_reg_recent,128);pc=ngb_reg_current_va;wrd=MEM32(0xdb67c0);ticks=ngb_guest_polls;entry=ngb_reg_entries;
   g_regs=r0;ngb_reg_current_va=pc0;ngb_guest_polls=t0;ngb_reg_entries=e0;
   memcpy(ngb_reg_recent,rcs,128);memcpy(ngb_fast_ram+sp_save-256,st0,400);memcpy(ngb_fast_ram+0x950180,m0,64);
   MEM32(0xdb67c0)=w0;for(unsigned j=0;j<n;j++)memcpy(ngb_fast_ram+addresses[j],vs0[j],4);
  }
 }
''')
k='loc_0013D550: ;'
s=s.replace(k,k+'''
 if(remain && !--remain){
  unsigned sd=0,rd=0,ad=0;
  for(unsigned i=0;i<400;i++)if(st[i]!=ngb_fast_ram[sp_save-256+i]){if(sd++<10)leaf_log("[GROUP_STACK] off=%d opt=%02x ref=%02x\\n",(int)i-256,st[i],ngb_fast_ram[sp_save-256+i]);}
  for(unsigned i=0;i<sizeof reg;i++)if(((uint8_t*)&reg)[i]!=((uint8_t*)&g_regs)[i]){if(rd++<6)leaf_log("[GROUP_REG] off=%u opt=%02x ref=%02x\\n",i,((uint8_t*)&reg)[i],((uint8_t*)&g_regs)[i]);}
  for(unsigned j=0;j<group_size;j++)ad+=!!memcmp(endw[j],ngb_fast_ram+addresses[j],4);
  if(sd||rd||ad||memcmp(mat,ngb_fast_ram+0x950180,64)||memcmp(rc,ngb_reg_recent,128)||pc!=ngb_reg_current_va||wrd!=MEM32(0xdb67c0)||ticks!=ngb_guest_polls||entry!=ngb_reg_entries){
   leaf_log("[GROUP_FAIL] group=%u stack=%u regs=%u actor=%u tickets=%lld entries=%lld\\n",group_size,sd,rd,ad,(long long)(ngb_guest_polls-ticks),(long long)(ngb_reg_entries-entry));__builtin_trap();
  }
  groups[group_size]++;if(!(++ok%2048))leaf_log("[GROUP_OK] checked=%u n2=%u n3=%u n4=%u n5=%u n6=%u n7=%u n8=%u n9=%u\\n",ok,groups[2],groups[3],groups[4],groups[5],groups[6],groups[7],groups[8],groups[9]);
 }
''')
f=d/'shadow.c';f.write_text(s);n='recomp_0009.c'
c=next(shlex.split(l) for l in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if l.endswith('/'+n));o=str(d/'shadow.o')
c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=w,check=True)
