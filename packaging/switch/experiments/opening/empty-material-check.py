"""Differential test of the actual fast-path C against the guest's null path.
An unsuccessful guard must leave every observable byte untouched."""
import runpy,tempfile,subprocess
from pathlib import Path
helper=runpy.run_path(str(Path(__file__).with_name('empty-material.py')))['helper']
s=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef struct { unsigned ax,sp,si,va,hist[32]; uint64_t ent,polls; unsigned mem[2048]; } S;
static S a,b;
static unsigned char *ngb_fast_ram=(unsigned char*)a.mem;
static uint16_t ngb_fast_page_bytes[1<<20];
unsigned ngb_pending_dpcs,ngb_poll_mask;
#define eax a.ax
#define esp a.sp
#define esi a.si
#define ngb_reg_entries a.ent
#define ngb_reg_current_va a.va
#define ngb_reg_recent a.hist
#define ngb_guest_polls a.polls
'''
s+=helper[helper.index('static inline'):]
s+=r'''
int main(void){
 unsigned hits=0,miss=0,seed=97;
 for(unsigned i=0;i<80000;i++){
  seed=seed*1664525u+1013904223u;
  a.sp=(seed&0x1ffc)+8;if(i&1)a.sp|=0x80000000;
  if(i%7==0)++a.sp;
  a.ax=i%9==0?0x12345:0;a.si=seed^123;
  a.ent=(i%13==0)?47:(uint64_t)i+50;a.polls=(i%19==0)?UINT64_MAX:i;
  ngb_pending_dpcs=(i%17==0);ngb_poll_mask=(i&1)?63:255;
  unsigned lo=a.sp-8,page=lo>>12;ngb_fast_page_bytes[page]=i%11?4096:0;
  unsigned valid=!a.ax&&!((a.sp-8)&3)&&((lo&4095)+8<=ngb_fast_page_bytes[page])&&
    ((a.polls+1)&ngb_poll_mask)&&!ngb_pending_dpcs&&a.ent>=48;
  b=a;unsigned ret=i%3==0?0x30bcda:i%3==1?0x30c064:0x30c0bc;
  if(valid){b.sp-=4;b.mem[(b.sp&8191)/4]=ret;b.va=0x30c240;b.hist[b.ent++%32]=b.va;b.polls++;
    b.sp-=4;b.mem[(b.sp&8191)/4]=b.si;b.si=b.ax;b.si=b.mem[(b.sp&8191)/4];b.sp+=8;}
  int ok=empty_material(ret);assert(ok==valid && !memcmp(&a,&b,sizeof a));if(ok)hits++;else miss++;
 }printf("original null path %u matches; %u unchanged guard misses\n",hits,miss);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 f=Path(tmp)/'empty.c';f.write_text(s);binary=f.with_suffix('')
 subprocess.run(['cc','-O2',f,'-o',binary],check=True)
 subprocess.run([binary],check=True)
