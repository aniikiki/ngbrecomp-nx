"""Keep interrupted registers, and format only after all 120 frames."""
def install(s):
    for key,new in [
        ('static void pc_sample', 'static uintptr_t op_regs[8192][32];\nstatic void pc_sample'),
        ('if(pc_used<8192){','if(pc_used<8192){for(int n=0;n<31;n++)op_regs[pc_used][n]=((ucontext_t*)ctx)->uc_mcontext.regs[n];op_regs[pc_used][31]=((ucontext_t*)ctx)->uc_mcontext.sp;'),
        (' for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_PC]', r''' for(int j=0;j<pc_used;j++){fprintf(stderr,"[OPREG] %u %lx",pc_rows[j].frame,(unsigned long)pc_rows[j].pc);for(int n=0;n<32;n++)fprintf(stderr," %lx",(unsigned long)op_regs[j][n]);fputc('\n',stderr);}
 for(int j=0;j<pc_used;j++)fprintf(stderr,"[FRAME_PC]''')]:
        assert s.count(key)==1
        s=s.replace(key,new)
    return s
