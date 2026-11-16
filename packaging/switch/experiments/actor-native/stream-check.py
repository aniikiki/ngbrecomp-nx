"""Compare compact and raw objects on the same job at EVERY poll. Compare
all store masks (including stores of unchanged values), registers and bytes."""
from pathlib import Path
import subprocess as sp
here=Path(__file__).resolve().parent;p=Path('/work/build/switch-runtime');d=p/'opt050/actor-stream';raw=d.parent/'actor-journal'
s=(here/'replay.c').read_text();a=s.index('static void *run(');s=s[:a]+r'''
typedef unsigned (*compute)(void*,uint8_t*,const uint16_t*,uint64_t*,uint64_t*,uint8_t*,unsigned,unsigned*,uint32_t*,unsigned*);
extern unsigned raw_worker(void*,uint8_t*,const uint16_t*,uint64_t*,uint64_t*,uint8_t*,unsigned,unsigned*,uint32_t*,unsigned*);
extern unsigned stream_worker(void*,uint8_t*,const uint16_t*,uint64_t*,uint64_t*,uint8_t*,unsigned,unsigned*,uint32_t*,unsigned*);
int main(int argc,char**argv){struct job j={0};if(argc!=2||!load(&j,argv[1]))return 2;
 uint32_t(*log[2])[3];uint8_t *tr[2],regs[2][512];unsigned n[2],events[2];uint64_t entries[2],ticks[2];
 for(unsigned mode=0;mode<2;mode++){memcpy(j.ram,j.init,RAM);memcpy(regs[mode],j.regs,j.meta[3]);
 ticks[mode]=j.ticks;tr[mode]=calloc(8192,520);log[mode]=malloc(524288*12);if(!tr[mode]||!log[mode])return 3;
 unsigned err=(mode?stream_worker:raw_worker)(regs[mode],j.ram,j.pages,&ticks[mode],&entries[mode],tr[mode],520,&events[mode],log[mode][0],&n[mode]);
 if(err||memcmp(regs[mode],j.expect,j.meta[3]))return 4;}
 if(events[0]!=events[1]||entries[0]!=entries[1]||ticks[0]!=ticks[1]||memcmp(tr[0],tr[1],520*(events[0]+1)))return 5;
 uint32_t a=0,b=0;unsigned char*mask=calloc(RAM,1),*val=malloc(RAM);if(!mask||!val)return 6;
 for(unsigned k=0;k<=events[0];k++){unsigned lo=a;
   while(a<n[0]&&log[0][a][0]==k){unsigned*e=log[0][a++];mask[e[1]]=1;val[e[1]]=e[2];}
   while(b<n[1]&&(log[1][b][0]>>4)==k){unsigned*e=log[1][b++];for(unsigned z=0;z<4;z++)if(e[0]&(1<<z)){
     unsigned addr=e[1]+z;if(mask[addr]!=1||val[addr]!=(uint8_t)(e[2]>>(8*z)))return 7;mask[addr]=0;}}
   for(unsigned i=lo;i<a;i++)if(mask[log[0][i][1]])return 8;
 }
 if(a!=n[0]||b!=n[1])return 9;
 printf("[STREAM_EXACT] id=%u polls=%u raw=%u records=%u registers_and_masks_identical=1\n",j.meta[2],events[0],a,b);
}
'''
(d/'check.c').write_text(s)
objs=[]
for dirname,name in [(raw,'raw_worker'),(d,'stream_worker')]:
 dst=d/(name+'.o');sp.run(['objcopy','--redefine-sym','ngb_actor_native='+name,dirname/'actor.o',dst],check=True)
 # Each object's internal sanitizer hooks resolve against its own compiled code.
 symbols=sp.check_output(['nm','-g','--defined-only',dst],text=True);private=[l.split()[-1] for l in symbols.splitlines() if 'private___tsan' in l]
 sp.run(['objcopy',*['--localize-symbol='+x for x in private],dst],check=True);objs.append(dst)
sp.run(['cc','-O2','-I'+str(here),d/'check.c',*objs,p/'core-perf/thread-pointer.o','-l:libz.so.1','-pthread','-lm','-o',d/'check'],check=True)
