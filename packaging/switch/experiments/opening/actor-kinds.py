"""Histogram the actual recursive model node discriminator, including slow-page reads."""
import re,subprocess
def install(p,regs,src):
 name='recomp_0016.c';s=(regs/(name+'.gated.s')).read_text()
 a=s.index('ngb_reg_sub_001CBED0:\n');z=s.index('\t.size\tngb_reg_sub_001CBED0',a);b=s[a:z]
 k='.L40789:\n\tldr\tw0, [x0]\n';assert b.count(k)==1 and not re.search(r'\b[wx](?:16|17)\b',b)
 # Do not change flags or guest registers. Bucket 16 means all unsigned values >=16.
 b=b.replace(k,k+''' mov w16,#16
 cmp w0,w16
 csel w16,w0,w16,lo
 adrp x17,kind_counts
 add x17,x17,:lo12:kind_counts
 add x17,x17,x16,lsl #2
 ldr w16,[x17]
 add w16,w16,#1
 str w16,[x17]
''');assert '\tmov\tw21, w0\n\tcmp\tw0, 1\n' in b # NZCV overwritten before use
 # Slow path returns to the same load point.
 assert re.search(r'\.L40788:.*?\bb\s+\.L40789\b',b,re.S)
 f=p.out/'kind.s';obj=f.with_suffix('.o');f.write_text(s[:a]+b+s[z:]);subprocess.run(['cc','-c',f,'-o',obj],check=True);f.unlink()
 p.link[p.link.index(str(regs/(name+'.o')))]=str(obj)
 return src.replace('void __real_ngb_kernel_log',r'''
unsigned kind_counts[17];
void phase_flip(unsigned f){if(f==30||f==120){fprintf(stderr,"[ACTOR_KINDS] %u",f);for(unsigned i=0;i<17;i++)fprintf(stderr," %u",kind_counts[i]);fputc(10,stderr);}
 if(!f||f==30){memset(kind_counts,0,sizeof kind_counts);}}
void __real_ngb_kernel_log''',1)
