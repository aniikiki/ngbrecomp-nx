"""Use a snapshot only for ordinary RAM with a byte-exact, FP-compatible hit."""
from pathlib import Path
import os,sys,re
base=Path('build/switch-runtime');p=Path(__file__).resolve().parent
def transform(s):
 k='#include "matrix.h"'
 assert s.count(k)==1 and s.count('if (ngb_matrix_product(')==1
 cache=r'''
extern unsigned product_audit,product_checked;
struct product_slot {uint32_t l,r,valid,ctrl,status; unsigned char in[128],out[96];};
static struct product_slot products[4096];
static inline bool cached_product(unsigned l,unsigned r){
 if((l&4095u)+64>ngb_fast_page_bytes[l>>12] || (r&4095u)+64>ngb_fast_page_bytes[r>>12])return ngb_matrix_product(l,r);
 unsigned char *a=ngb_fast_ram+(l&0x7fffffffu),*b=ngb_fast_ram+(r&0x7fffffffu);
 unsigned h=(l>>4)*2654435761u^(r>>4)*2246822519u;h^=h>>16;
 struct product_slot *v=&products[h&4095];uint64_t ctrl,status;
 __asm__ volatile("mrs %0,fpcr\n mrs %1,fpsr":"=r"(ctrl),"=r"(status)::"memory");
 if(ctrl&0x9f00u)return ngb_matrix_product(l,r);
 if(v->valid && v->l==l && v->r==r && v->ctrl==ctrl && !(v->status&~status)
 && !memcmp(a,v->in,64) && !memcmp(b,v->in+64,64)){
 if(product_audit){
 if(!ngb_matrix_product(l,r))__builtin_trap();
 AUDIT_OUTPUT
 uint64_t post;__asm__ volatile("mrs %0,fpsr":"=r"(post)::"memory");
 if(post!=status)__builtin_trap();
 ++product_checked;}
 RESTORE_OUTPUT
 return true;}
 if(!ngb_matrix_product(l,r))return false;
 __asm__ volatile("mrs %0,fpsr":"=r"(status)::"memory");
 v->valid=1;v->l=l;v->r=r;v->ctrl=ctrl;v->status=status;
 memcpy(v->in,a,64);memcpy(v->in+64,b,64);
 SAVE_OUTPUT
 return true;}
'''
 for tag,fmt in [('AUDIT_OUTPUT','if(memcmp(&g_xmm{},v->out+{},16))__builtin_trap();'),('SAVE_OUTPUT','memcpy(v->out+{1},&g_xmm{0},16);'),('RESTORE_OUTPUT','memcpy(&g_xmm{},v->out+{},16);')]:
  cache=cache.replace(tag,'\n'.join(fmt.format(i,16*i) for i in range(6)))
 return s.replace('if (ngb_matrix_product(','if (cached_product(').replace(k,k+'\n'+cache),None
src=(p/'vector-span.py').read_text().split("if __name__=='__main__':",1)[1]
exec(compile('if True:'+src.replace('units=[16,28,29]','units=[29]').replace('opening-vector-span','opening-product-cache'),'product-cache-build','exec'))
