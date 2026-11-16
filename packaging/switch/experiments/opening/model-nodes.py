"""Observe the original material command lists, never skip or replay commands.
Count function entries and *executed* nodes by opcode; the entry count includes empty lists."""
from pathlib import Path
import subprocess as sp
def install(p,regs,src):
    asm=(regs/'recomp_0028.c.gated.s').read_text()
    start=asm.index('ngb_reg_sub_0030C240:\n');end=asm.index('.size\tngb_reg_sub_0030C240,',start)
    body=asm[start:end]
    for k,idx in [('mov\tw24, w19\n\tcbz\tw19,','mov w16,#256'),('cmp\tw1, 254\n\tbne','and w16,w19,#255'),('cmp\tw1, 254\n\tbeq','and w16,w19,#255'),('cbz\tw19, .L15380','mov w16,#257\n cbnz w19,91f')]:
        assert body.count(k)==1,k
        # None of NZCV/x0..x15 are changed; x16/x17 are not live in this body.
        assert 'x17' not in asm[start:end] and 'w16' not in asm[start:end] and 'x16' not in asm[start:end].replace('mov x16,x0','') and 'w17' not in asm[start:end]
        at=body.index(k)
        prefix='' if '91f' not in idx else '91:\n'
        body=body[:at]+idx+'\n adrp x17,node_rows\n add x17,x17,:lo12:node_rows\n add x17,x17,x16,lsl #2\n ldr w16,[x17]\n add w16,w16,#1\n str w16,[x17]\n '+prefix+body[at:]
    asm=asm[:start]+body+asm[end:]
    f=p.out/'node.s';obj=f.with_suffix('.o');f.write_text(asm);sp.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
    # Assembly uses the 14-unit private ABI and gates, so use the matching baseline.
    p.link[p.link.index(str(regs/'recomp_0028.c.o'))]=str(obj)
    return src.replace('void __real_ngb_kernel_log','''unsigned node_rows[258];
void node_flip(unsigned f){
 if(f==30||f==120){fprintf(stderr,"[MODEL_NODES] %u",f);for(unsigned i=0;i<258;i++)if(node_rows[i])fprintf(stderr," %u:%u",i,node_rows[i]);fputc(10,stderr);}
 if(f==0||f==30)memset(node_rows,0,sizeof node_rows);
}
void __real_ngb_kernel_log''',1)
