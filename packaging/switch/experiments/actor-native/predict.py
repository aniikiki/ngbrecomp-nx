"""Isolate speculative input errors by swapping register file, stack and world
independently. Never publish worker memory. Requires replay-sparse.py first."""
from pathlib import Path
import subprocess as sp
d=Path('/work/build/switch-runtime/opt050/actor-sparse')
s=(d/'test.c').read_text().split('static void *run(')[0]+r'''
static uint32_t word(const uint8_t*p,uint32_t x){uint32_t v;x&=0x7fffffff;if(x>RAM-4)abort();memcpy(&v,p+x,4);return v;}
int main(int argc,char**argv){struct job b={0},t={0};if(argc!=3||!load(&b,argv[1])||!load(&t,argv[2]))return 2;
 unsigned sp=b.meta[5]&0x7fffffff,id=t.meta[2],k=0;while(k<32&&b.init[sp+24+k]!=id)k++;
 if(k==32||sp!=(t.meta[5]&0x7fffffff))return 3;
 for(unsigned mode=0;mode<12;mode++){
 uint8_t*ram=b.ram;memcpy(ram,(mode&4)?t.init:b.init,RAM);
 if(mode>=8){for(unsigned q=0;q<b.meta[4];q++){unsigned a=b.at[q];if(a>=sp-16384 && a<sp)ram[a]=b.bytes[q];}}
 if(mode&2)memcpy(ram+sp-16384,t.init+sp-16384,16640);
 ram[sp+20]=id;
 uint32_t r[128]={0};memcpy(r,mode>=8?b.expect:b.regs,b.meta[3]);uint32_t obj=0x4b4e50+0x2800u*id;
 r[3]=((uint32_t*)b.regs)[3];r[4]=((uint32_t*)b.regs)[4]-k;r[6]=obj;r[0]=word(ram,obj+0x26d8);r[1]=0;
 if(r[0]){r[2]=word(ram,r[0]+24);r[0]=word(ram,r[0]+r[2]);if(r[0]){r[1]=word(ram,r[0]+4);if(r[1]){r[1]=word(ram,r[0]+r[1]);if(r[1])r[1]+=r[0];}}}
 if(mode&1)memcpy(r,t.regs,t.meta[3]);
 uint32_t predicted[128];memcpy(predicted,r,sizeof r);
 uint64_t ticks=t.ticks,en=0;memset(b.index,0,65536);unsigned used=0;
 unsigned err=ngb_actor_sparse(r,ram,t.pages,&ticks,&en,b.index,b.slots,b.touched,&used);
 unsigned nr=0,nm=0;for(unsigned i=0;i<t.meta[3];i++){if(((uint8_t*)r)[i]!=t.expect[i]){if(mode==8)printf(" reg byte %u predicted-in=%02x correct-in=%02x got=%02x want=%02x\n",i,((uint8_t*)predicted)[i],t.regs[i],((uint8_t*)r)[i],t.expect[i]);nr++;}}
 for(unsigned i=0;i<t.meta[4];i++){unsigned a=t.at[i],slot=b.index[a>>12];unsigned v=slot?b.slots[(slot-1)*4096+(a&4095)]:ram[a];if(v!=t.bytes[i]){if(mode==8)printf(" address %08x sp%+d got=%02x want=%02x\n",a,(int)(a-sp),v,t.bytes[i]);nm++;}}
 printf("id=%u pos=%u mode=%u error=%x reg_errors=%u write_errors=%u\n",id,k,mode,err,nr,nm);
 if(mode==7&&(err||nr||nm))return 4;
 }return 0;}
'''
(d/'predict.c').write_text(s)
sp.run(['cc','-O2','-I'+str(Path(__file__).resolve().parent),d/'predict.c',d/'actor.o',d.parent.parent/'core-perf/thread-pointer.o','-l:libz.so.1','-lm','-o',d/'predict'],check=True)
