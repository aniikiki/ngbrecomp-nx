"""Time both model-list indirect dispatch sites by actual guest target. Restore
the parent key on return and the suspended key across fiber switches."""
from pathlib import Path
import subprocess as sp
import re
def install(p,regs,rt,src,outer=False,branches=False):
 s=(regs/'recomp_0028.c.gated.s').read_text()
 for fn,off in [('00308CE0',28),('00308D50',16)]+([('0030C8B0',16)] if outer else []):
    a=s.index('ngb_reg_sub_'+fn+':\n');z=s.index('\t.size\tngb_reg_sub_'+fn,a)
    body=s[a:z]
    if fn=='0030C8B0':
        k='\tadrp\tx3, :got:g_icall_trace\n';assert body.count(k)==1
        body=body.replace(k,' str w2,[sp,#16]\n'+k)
    else:
        assert f'str\tw2, [sp, {off}]\n\tbl\trecomp_lookup_manual' in body
    k='mov x16,x0\n\tbl ngb_gate_indirect';assert body.count(k)==1
    body=body.replace(k,f'''ldr w1,[sp,#{off}]
 stp x0,x30,[sp,#-16]!
 mov w0,w1
 bl cb_enter
 mov w1,w0
 ldr x16,[sp]
 str w1,[sp]
 bl ngb_gate_indirect
 ldr w0,[sp]
 bl cb_switch
 ldp x16,x30,[sp],#16''')
    s=s[:a]+body+s[z:]
 f=p.out/'cb.s';obj=f.with_suffix('.o');f.write_text(s);sp.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
 p.link[p.link.index(str(regs/'recomp_0028.c.o'))]=str(obj)
 if branches:
    asm=(regs/'recomp_0016.c.gated.s').read_text()
    wrappers=[];sites=[]
    for fn in ('001CB9A0','001CBA70','001CC300','001CC5A0','001CBD00','001CBED0'):
        a=asm.index('ngb_reg_sub_'+fn+':\n');z=asm.index('\t.size\tngb_reg_sub_'+fn,a)
        def wrap(m):
            name=m[1];i=len(wrappers)+1
            # Private and gate guest functions take arguments in the guest register
            # bank. Keep its call ABI and the indirect dispatcher on the original stack.
            wrappers.append(f'.Lcb_edge{i}:\n stp x29,x30,[sp,#-32]!\n mov x29,sp\n mov w0,#{i}\n movk w0,#0xbd00,lsl #16\n bl cb_enter\n str w0,[sp,#16]\n bl {name}\n ldr w0,[sp,#16]\n bl cb_switch\n ldp x29,x30,[sp],#32\n ret\n')
            sites.append(f'{0xbd000000+i:x} {fn} {name}')
            return f'bl .Lcb_edge{i}'
        body=re.sub(r'\bbl\s+(ngb_(?:reg|gate)_sub_[0-9A-F]+)\b',wrap,asm[a:z]);asm=asm[:a]+body+asm[z:]
    assert 40<len(sites)<150
    f=p.out/'cb-edges.s';obj=f.with_suffix('.o');f.write_text(asm+'\n.text\n'+''.join(wrappers))
    sp.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
    p.link[p.link.index(str(regs/'recomp_0016.c.o'))]=str(obj)
    (p.out/'edges.txt').write_text('\n'.join(sites)+'\n')
 w=(rt/'workers.inc').read_text()
 for t in ('worker','fiber'):
    k='static struct '+t+' {';assert w.count(k)==1;w=w.replace(k,k+'\n unsigned cb_slot;')
 for k in ('next','dest'):
    q=f'ngb_ctx_switch(&old->sp, {k}->sp);';assert w.count(q)==1;w=w.replace(q,f'old->cb_slot=cb_switch({k}->cb_slot); '+q)
 (p.out/'workers.inc').write_text('unsigned cb_switch(unsigned);\n'+w)
 k='void __real_ngb_kernel_log'
 return src.replace(k,r'''
static unsigned cb_key[2048],cb_n[2048],cb_active,cb_slot;
static uint64_t cb_ns[2048],cb_last,cb_start;
static uint64_t cb_now(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
unsigned cb_switch(unsigned i){
 unsigned prev=cb_slot;if(cb_active){uint64_t t=cb_now();cb_ns[prev]+=t-cb_last;cb_last=t;}cb_slot=i;return prev;}
unsigned cb_enter(unsigned key){
 if(!key){abort();} unsigned i=1+(key>>4)%2047;
 for(unsigned n=0;cb_key[i] && cb_key[i]!=key;n++){if(n==2046)abort();if(++i==2048)i=1;}
 cb_key[i]=key;if(cb_active)cb_n[i]++;return cb_switch(i);}
void cb_flip(unsigned f){
 if(f!=0 && f!=30 && f!=120)return;
 if(f){uint64_t t=cb_now(),sum=0;cb_ns[cb_slot]+=t-cb_last;for(unsigned i=0;i<2048;i++)if(cb_ns[i]||cb_n[i]){
 fprintf(stderr,"[CB_COST] %u %x %u %llu\n",f,cb_key[i],cb_n[i],(unsigned long long)cb_ns[i]);sum+=cb_ns[i];}
 if(sum!=t-cb_start)abort();}
 memset(cb_ns,0,sizeof cb_ns);memset(cb_n,0,sizeof cb_n);cb_active=f!=120;cb_last=cb_start=cb_now();}
'''+k,1)
