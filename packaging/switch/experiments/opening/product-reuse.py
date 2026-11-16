"""Observe exact input-byte reuse at real 328232 calls. Never replace a product."""
import subprocess
def install(p,regs,src):
 name='recomp_0029.c';s=(regs/(name+'.gated.s')).read_text()
 a=s.index('ngb_reg_sub_00328232:\n');z=s.index('\t.size\tngb_reg_sub_00328232',a);k='bl ngb_reg_checkpoint\n';b=s[a:z];assert b.count(k)==1
 s=s[:a]+b.replace(k,k+' mov x0,x26\n mov w1,w22\n bl product_observe\n')+s[z:]
 f=p.out/'product.s';obj=f.with_suffix('.o');f.write_text(s);subprocess.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
 p.link[p.link.index(str(regs/(name+'.o')))]=str(obj)
 return src.replace('void __real_ngb_kernel_log',r'''
struct prod_row {unsigned valid,l,r,f,caller; unsigned char inputs[128];};
static struct prod_row prod[4096];static unsigned pf,pn[9];
static const unsigned char *product_ptr(const unsigned char*r,unsigned a,unsigned n){
 return (a&4095u)+n<=ngb_fast_page_bytes[a>>12]?r+(a&0x7fffffffu):NULL;}
void product_observe(unsigned char *ram,unsigned sp){
 if(!pf){return;}pn[0]++;
 const unsigned char*k=product_ptr(ram,sp,16);if(!k)return;
 unsigned v[4];memcpy(v,k,16);
 const unsigned char *l=product_ptr(ram,v[2],64),*r=product_ptr(ram,v[3],64);
 if(!l||!r){return;}pn[1]++;
 unsigned h=((v[2]>>4)*2654435761u^(v[3]>>4)*2246822519u);h^=h>>16;
 struct prod_row *q=&prod[h&4095];
 if(q->valid && q->l==v[2] && q->r==v[3]){
 ++pn[2];int sl=!memcmp(l,q->inputs,64),sr=!memcmp(r,q->inputs+64,64);
 pn[3]+=sl;pn[4]+=sr;if(sl&&sr){pn[5]++;pn[6]+=q->f==pf;pn[7]+=q->caller==v[0];}
 }else if(q->valid)pn[8]++;
 q->valid=1;q->l=v[2];q->r=v[3];q->f=pf;q->caller=v[0];memcpy(q->inputs,l,64);memcpy(q->inputs+64,r,64);}
void phase_flip(unsigned f){if(f==30||f==120){fprintf(stderr,"[PRODUCT_REUSE] %u",f);for(unsigned i=0;i<9;i++)fprintf(stderr," %u",pn[i]);fputc(10,stderr);}
 if(!f||f==30){memset(pn,0,sizeof pn);}pf=f<120?f+1:0;}
void __real_ngb_kernel_log''',1)
