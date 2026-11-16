"""Compare shallow metadata across the two real actor phases. Never reuse a
prior result in this observer; unreadable or ambiguous keys cannot count."""
from pathlib import Path
import subprocess as sp
def install(p,regs,src):
 s=(regs/'recomp_0016.c.gated.s').read_text()
 for fn,actor,phase in [('001CC430',23,0),('001CC6E0',25,1)]:
    a=s.index('ngb_reg_sub_'+fn+':\n');z=s.index('\t.size\tngb_reg_sub_'+fn,a);b=s[a:z]
    k='bl ngb_reg_checkpoint\n';assert b.count(k)==1
    b=b.replace(k,k+f' mov x0,x26\n mov w1,w{actor}\n mov w2,w19\n mov w3,#{phase}\n bl actor_observe\n');s=s[:a]+b+s[z:]
 f=p.out/'phase.s';obj=f.with_suffix('.o');f.write_text(s);sp.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
 p.link[p.link.index(str(regs/'recomp_0016.c.o'))]=str(obj)
 return src.replace('void __real_ngb_kernel_log',r'''
struct actor_phase_row{unsigned frame,actor,idx,v[7],amb;};
static struct actor_phase_row phase_rows[4096];static unsigned phase_frame,phase_n[8];
static int ar_read(unsigned char*r,uint64_t va,unsigned n,unsigned*out){
 if(va>UINT32_MAX || (va&0x7fffffffu)>=0x8000000u || (va&4095)+n>ngb_fast_page_bytes[va>>12])return 0;
 *out=0;memcpy(out,r+((unsigned)va&0x7fffffffu),n);return 1;}
void actor_observe(unsigned char*r,unsigned obj,unsigned idx,unsigned phase){
 if(!phase_frame){return;} ++phase_n[phase];unsigned v[7];
 if(!ar_read(r,(uint64_t)obj+idx+0x27d0,1,v)||!ar_read(r,(uint64_t)obj+4ull*idx+0x26e8,4,v+1)||
 !ar_read(r,(uint64_t)obj+0x26dc,4,v+2)||!ar_read(r,v[2],4,v+3)||
 !ar_read(r,(uint64_t)v[3]+0x18,4,v+4)||!ar_read(r,(uint64_t)v[3]+v[4]+8,4,v+5)){
 ++phase_n[2];return;}v[6]=0;
 unsigned i=((obj>>4)*2654435761u+idx*131u)&4095;
 for(unsigned j=0;j<4096;j++,i=(i+1)&4095){struct actor_phase_row *q=phase_rows+i;
 if(q->frame==phase_frame && (q->actor!=obj||q->idx!=idx))continue;
 if(!phase){if(q->frame==phase_frame){q->amb=1;phase_n[3]++;return;}
 *q=(struct actor_phase_row){phase_frame,obj,idx,{0},0};memcpy(q->v,v,sizeof v);}
 else if(q->frame==phase_frame && !q->amb){phase_n[4]++;phase_n[5]+=!memcmp(q->v,v,sizeof v);}
 else {phase_n[6]++;}return;}++phase_n[7];}
void phase_flip(unsigned f){if(f==30||f==120){fprintf(stderr,"[ACTOR_PHASE] %u",f);for(unsigned i=0;i<8;i++)fprintf(stderr," %u",phase_n[i]);fputc(10,stderr);}
 if(!f||f==30)memset(phase_n,0,sizeof phase_n);
 phase_frame=f<120?f+1:0;}
void __real_ngb_kernel_log''',1)
