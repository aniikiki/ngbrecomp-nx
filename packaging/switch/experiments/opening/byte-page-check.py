"""Compare the real scalar helpers for every page offset, both aliases and
both page-map states (including changes); check width and fallback address."""
from pathlib import Path
import runpy,subprocess,tempfile,sys
p=Path(__file__).resolve().parent
s=(p.parents[1]/'runtime/guest_memory.h').read_text()
def body(s):
 a=s.index('static inline __attribute__((always_inline)) uintptr_t ngb_guest_scalar(')
 return s[a:s.index('static inline uintptr_t ngb_guest_scalar_paged',a)]
c='''
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#define ngb_static_image_span(a,b) 0
static unsigned char *ngb_fast_ram=(void*)(uintptr_t)0x100000000ull;
static uint16_t ngb_fast_page_bytes[1<<20];
static unsigned slow,va,width;
static uintptr_t ngb_guest_scalar_fallback(unsigned a,size_t n){slow++;va=a;width=n;return 0;}
'''
for n,t in enumerate((s,runpy.run_path(str(p/('word-page.py' if '--word' in sys.argv else 'byte-page.py')))['edit'](s))):
 c+=body(t).replace('uintptr_t ngb_guest_scalar(','uintptr_t access'+str(n)+'(')
c+='''
int main(void){unsigned count=0;unsigned pages[]={0,7,4096,0x3fff,0x80000,0x83fff,0xfffff};
for(unsigned i=0;i<7;i++)for(unsigned state=0;state<6;state++){
 unsigned pg=pages[i];ngb_fast_page_bytes[pg]=state==1?4096:state==2?4093:state==3?1:state==4?1024:0;
 for(unsigned j=0;j<4096;j++){volatile unsigned v=(pg<<12)+j;
#define CHECK(n) do{slow=va=width=0;uintptr_t x=access0(v,n);unsigned l=slow,a=va,w=width;slow=va=width=0;uintptr_t y=access1(v,n);assert(x==y&&l==slow&&a==va&&w==width);count++;}while(0)
 CHECK(1);CHECK(2);CHECK(4);CHECK(8);
 }}
printf("%u matching translations and fallback traces\\n",count);}
'''
with tempfile.TemporaryDirectory() as d:
 f=Path(d)/'check.c';exe=f.with_suffix('');f.write_text(c)
 subprocess.run(['cc','-O2',str(f),'-o',str(exe)],check=True);subprocess.run([exe],check=True)
