"""Capture the currently committed low prefix at the actual indexed guest-page load."""
def vm(s):
 k='uint32_t opening_end4[1u<<20];';assert s.count(k)==1
 s=s.replace(k,k+'''
volatile unsigned lp_end_page;
static void lp_refresh(void){
 unsigned p=8;while(p<NGB_VM_END/4096 && opening_end4[p]==(p<<12)+4093u)++p;
 lp_end_page=p;
}
''')
 k='    memset(pages, 0, sizeof(pages));'
 assert s.count(k)==1;s=s.replace(k,k+' lp_refresh();')
 a=s.index('uint32_t ngb_vm_query')
 assert s[:a].count('    *base = ')==2
 return s[:a].replace('    *base = ','    lp_refresh();\n    *base = ')+s[a:]
def instrument(s):
 k='static unsigned page_rows[8192][2]'
 assert s.count(k)==1;s=s.replace(k,'extern volatile unsigned lp_end_page;\nstatic unsigned page_rows[8192][3]')
 k='page_rows[pc_used][1]=(unsigned)page;';assert s.count(k)==1
 s=s.replace(k,k+'page_rows[pc_used][2]=lp_end_page;')
 return s.replace('[PAGE_PC] %u %lx %x','[LOW_PREFIX] %u %lx %x %x').replace('page_rows[j][1]);','page_rows[j][1],page_rows[j][2]);').replace('991027:887123','331027:287123')
