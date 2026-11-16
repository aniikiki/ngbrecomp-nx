"""Measure actual public-to-private ABI crossings; private direct calls bypass this file."""
import re,subprocess
def install(p,variant):
 s=(variant/'entry.S').read_text();names=[]
 def patch(m):
  i=len(names);names.append(m[1])
  return m[0]+f"""
 adrp x9,pe_active
 ldr w9,[x9,:lo12:pe_active]
 cbz w9,9f
 adrp x9,pe_count
 add x9,x9,:lo12:pe_count
 mov w10,#{i}
 ldr w11,[x9,w10,uxtw #2]
 add w11,w11,#1
 str w11,[x9,w10,uxtw #2]
9:"""
 s=re.sub(r'^([\w]+):(?=\n stp x29,x30,\[sp,-96\]!)',patch,s,flags=re.M)
 assert 1000<len(names)<65536 and len(names)==len(set(names))
 (p.out.parent/'public-names.txt').write_text('\n'.join(names)+'\n')
 asm=p.out/'public-entry.s';asm.write_text(s);o=asm.with_suffix('.o')
 subprocess.run(['cc','-c',asm,'-o',o],check=True)
 p.link[p.link.index(str(variant/'entry.o'))]=str(o)
 return f'unsigned pe_active,pe_count[{len(names)}];\n'+r"""
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<sizeof pe_count/sizeof pe_count[0];i++)
 if(pe_count[i])fprintf(stderr,"[PUBLIC_ENTRY] %u %u %u\n",f,i,pe_count[i]);
 if(!f||f==30)memset(pe_count,0,sizeof pe_count);
 pe_active=f<120;
}
"""
