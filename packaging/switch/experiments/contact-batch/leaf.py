from pathlib import Path
import subprocess as sp,sys,shlex
p=Path('/work/build/switch-runtime');d=p/'opt050/contact-leaf';w=p/'switch';n='recomp_0009.c'
s=(p/'gen'/n).read_text();tag='void sub_0013D330(void)\n{'
s=s.replace(tag,'extern unsigned ngb_reg_recent[32],ngb_reg_current_va;extern uint64_t ngb_reg_entries;\n'+Path(__file__).with_name('leaf.h').read_text().replace('#include "memo.inc"',Path(__file__).with_name('memo.inc').read_text())+'\n'+tag)
a='loc_0013D410: ; ngb_guest_block_poll();';b='loc_0013D550: ;'
if sys.argv[1]=='fast':
 s=s.replace(a,a+' if(contact_leaf(ebp))goto loc_0013D550;')
else:
 s=s.replace(tag,tag+'''
    extern void leaf_log(const char*,...);
    static unsigned round,ok;
    unsigned active=0,sp_save,ac_save;
    uint32_t rc[32],va_save,word;uint64_t ent,ticket;
    uint8_t st[400],mat[64],pos[4];RecompRegs reg;
''')
 s=s.replace(a,a+'''
    active=0;
    if(++round%7==0 && esp>0x1001000 && esp<0x3dfe000 && ngb_ram_span(esp-256,400) && ebx>=0x7a79c6 && ebx<=0x7a9000){
        unsigned sp=esp,ac=0x4b4e50+MEM8(ebx)*0x2800u;
        if(ac<0x7a0000){
            RecompRegs r0=g_regs;uint32_t rec[32],pc=ngb_reg_current_va,oldword=MEM32(0xdb67c0);
            uint64_t e=ngb_reg_entries,t=ngb_guest_polls;
            uint8_t so[400],mo[64],po[4];memcpy(so,ngb_fast_ram+sp-256,400);memcpy(mo,ngb_fast_ram+0x950180,64);memcpy(po,ngb_fast_ram+ac+0x8cc,4);memcpy(rec,ngb_reg_recent,128);
            if(contact_leaf(ebp)){
              active=1;reg=g_regs;sp_save=sp;ac_save=ac;memcpy(st,ngb_fast_ram+sp-256,400);memcpy(mat,ngb_fast_ram+0x950180,64);memcpy(pos,ngb_fast_ram+ac+0x8cc,4);
              memcpy(rc,ngb_reg_recent,128);ent=ngb_reg_entries;va_save=ngb_reg_current_va;word=MEM32(0xdb67c0);ticket=ngb_guest_polls;
              g_regs=r0;memcpy(ngb_reg_recent,rec,128);ngb_reg_entries=e;ngb_guest_polls=t;ngb_reg_current_va=pc;MEM32(0xdb67c0)=oldword;
              memcpy(ngb_fast_ram+sp-256,so,400);memcpy(ngb_fast_ram+0x950180,mo,64);memcpy(ngb_fast_ram+ac+0x8cc,po,4);
            }
        }
    }
''')
 s=s.replace(b,b+'''
    if(active){
     unsigned bad=0;
     for(unsigned i=0;i<sizeof reg;i++)if(((uint8_t*)&reg)[i]!=((uint8_t*)&g_regs)[i]){if(bad++<6)leaf_log("[LEAF_REG] off=%u opt=%02x ref=%02x\\n",i,((uint8_t*)&reg)[i],((uint8_t*)&g_regs)[i]);}
     for(unsigned i=0;i<400;i++)if(st[i]!=ngb_fast_ram[sp_save-256+i]){if(bad++<16)leaf_log("[LEAF_STACK] off=%d opt=%02x ref=%02x\\n",(int)i-256,st[i],ngb_fast_ram[sp_save-256+i]);}
     if(bad || memcmp(rc,ngb_reg_recent,128)||memcmp(mat,ngb_fast_ram+0x950180,64)||memcmp(pos,ngb_fast_ram+ac_save+0x8cc,4)||ent!=ngb_reg_entries||ticket!=ngb_guest_polls||word!=MEM32(0xdb67c0)||va_save!=ngb_reg_current_va){
       leaf_log("[LEAF_FAIL] n=%u bad=%u mat=%d tick=%lld ent=%lld va=%x/%x\\n",round,bad,memcmp(mat,ngb_fast_ram+0x950180,64),(long long)(ngb_guest_polls-ticket),(long long)(ngb_reg_entries-ent),va_save,ngb_reg_current_va);__builtin_trap();}
     if(!(++ok%4096))leaf_log("[LEAF_OK] n=%u checked=%u\\n",round,ok);active=0;
    }
''')
mode=sys.argv[1];f=d/(mode+'.c');f.write_text(s)
if mode=='shadow':
 c=next(shlex.split(l) for l in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=w,text=True).splitlines() if l.endswith('/'+n));o=str(d/'shadow.o')
 c[c.index('-o')+1]=o;c[c.index('-MF')+1]=o+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=w,check=True)
else:
 abi=Path('/work/packaging/switch/arm-registers')
 v=(abi/'compile.py').read_text().replace("o=w.parent/'native-regs'","o=w.parent/'opt050/contact-leaf'")
 v=v.replace(" sp.run(c,cwd=w,check=True)"," c[-1]=str(o/'fast.c')\n sp.run(c,cwd=w,check=True)",1)
 v=v[:v.index('with cf.ThreadPoolExecutor')]+"""build('recomp_0009.c')"""
 exec(compile(v,'leaf-private','exec'),{'__name__':'__main__'})
 v=(abi/'gates.py').read_text().replace('/switch-runtime/native-regs','/switch-runtime/opt050/contact-leaf')
 exec(compile(v,'leaf-gates','exec'),{'__name__':'__main__'})
