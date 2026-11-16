"""Run production fast-gate instructions against C reference; substitute a recording slow path."""
import ast,sys,platform,re,subprocess,tempfile
from pathlib import Path
p=Path(__file__).parent
tree=ast.parse((p/'gate-pointer.py').read_text())
fast=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==('mapped' if '--mapped' in sys.argv else 'fast'))
asm='.text\n.global candidate\ncandidate:\n'+fast+' b slow\n'
if platform.system()=='Darwin':
    asm=re.sub(r'adrp (x\d+),(ngb_\w+)',r'adrp \1,_\2@PAGE',asm)
    asm=re.sub(r':lo12:(ngb_\w+)',r'_\1@PAGEOFF',asm)
    asm=asm.replace('candidate','_candidate').replace(' b slow',' b _slow')
c=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
uint8_t *ngb_contiguous_pages[32768],ngb_vertex_dirty[32768],ngb_texture_dirty[32768],ngb_target_pages[32768];
int ngb_scene_active;
static uint8_t ram[4096];
static uint32_t sa; static size_t sn;static int sc;
uintptr_t slow(uint32_t a,size_t n){sa=a;sn=n;sc++;return 123;}
extern uintptr_t candidate(uint32_t,size_t);
int main(void){
 unsigned tested=0;
 uint32_t addresses[]={0x80000000,0x80001000,0x87fff000,0,0x7ffff000,0x88000000,0xfffff000};
 size_t widths[]={0,1,2,4,8,16,64,4096,4097,((size_t)1<<33)};
 for(unsigned k=0;k<7;k++)for(unsigned flags=0;flags<8;flags++)for(unsigned off=0;off<4096;off++)for(unsigned j=0;j<10;j++){
 uint32_t a=addresses[k]+off,phys=a-0x80000000u,pg=(phys>>12)&32767;size_t n=widths[j];
 ngb_scene_active=flags&1;ngb_contiguous_pages[pg]=(flags&2)?ram:0;ngb_target_pages[pg]=!!(flags&4);
 ngb_vertex_dirty[pg]=ngb_texture_dirty[pg]=0;sc=0;
 int hit=n && phys<0x08000000u && ngb_scene_active && ngb_contiguous_pages[pg] && !ngb_target_pages[pg] && (n==1?8:n)<=4096-off;
 if(candidate(a,n)!=(hit?(uintptr_t)(ram+off):123)||sc!=!hit||(!hit&&(sa!=a||sn!=n))||
 ngb_vertex_dirty[pg]!=hit||ngb_texture_dirty[pg]!=hit)abort();
 tested++;}
 printf("%u cases matched\n",tested);}
'''
if '--mapped' in sys.argv:
    c=c[:c.index('int main(void)')]+r"""
uint8_t *ngb_direct_pages[16384];
int main(void){
 unsigned tested=0;size_t widths[]={0,1,2,4,8,12,16,64,4095,4096,4097,((size_t)1<<33)};
 uint32_t bases[]={0,0x7000,0x8000,0xfff000,0x1000000,0x3fff000,0x4000000,0x80000000,0xfffff000};
 for(unsigned round=0;round<3;round++)for(unsigned k=0;k<9;k++)for(unsigned off=0;off<4096;off++)for(unsigned j=0;j<12;j++){
 uint32_t a=bases[k]+off;size_t n=widths[j];int valid=round==1 && k>=2 && k<=5;
 if(a<0x4000000)ngb_direct_pages[a>>12]=valid?ram:0;
 int hit=valid && n && n<=4096-off;
 sc=0;if(candidate(a,n)!=(hit?(uintptr_t)(ram+off):123)||sc!=!hit||(!hit&&(sa!=a||sn!=n)))abort();tested++;}
 printf("%u ordinary-page cases matched\n",tested);}
"""
with tempfile.TemporaryDirectory() as d:
    d=Path(d);(d/'gate.s').write_text(asm);(d/'test.c').write_text(c)
    subprocess.run(['cc','-O2',d/'test.c',d/'gate.s','-o',d/'check'],check=True);subprocess.run([d/'check'],check=True)
