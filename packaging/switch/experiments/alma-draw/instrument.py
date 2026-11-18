from pathlib import Path
import sys
source, native, output = map(Path, sys.argv[1:4])
s=source.read_text()
pre=r'''
static bool trial=false,fast=false;
static unsigned seq=0,idx=0,fresh=0,extraindices=0,linear=0,up=0,linhit=0,oldeligible=0,compact0=0;
static uint64_t threadtime(){timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec*1000000000ull+t.tv_nsec;}
extern "C" const uint32_t* ngb_scanout_last_pixels(void);
static void abflip(){
 static uint64_t prev=0,pwall=0;
 auto now=threadtime();timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);uint64_t wall=ts.tv_sec*1000000000ull+ts.tv_nsec;
 unsigned hp=kernel::R16(0x58a566),mx=kernel::R16(0x58a564);
 if(trial){static FILE*f=fopen("/probe/frames.csv","w");unsigned tot=idx+linear+up;
 fprintf(f,"%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%llu,%llu\n",seq,hp,fast,idx,linear,up,oldeligible,fresh,extraindices,linhit,unsigned(compact_draws)-compact0,(unsigned long long)(now-prev),(unsigned long long)(wall-pwall));
 if((seq&31)==0)fflush(f);
 if(hp>0&&hp<2400&&tot>300 && (seq&7)==6){static FILE*im=fopen("/probe/scanout.bin","wb");auto px=ngb_scanout_last_pixels();
 if(px){fwrite(&seq,4,1,im);for(unsigned y=4;y<480;y+=8) for(unsigned x=4;x<720;x+=8)fwrite(px+y*720+x,4,1,im);}}
 }
 ++seq;unsigned phase=(seq>>3)&3;fast=phase==1||phase==2;
 trial=g_backend&&!g_mirror&&ngb_scene_active&&kernel::R8(0x589758)==23&&kernel::R8(0x58975a)==3&&mx==2400&&hp;
 idx=linear=up=oldeligible=fresh=extraindices=linhit=0;compact0=unsigned(compact_draws);prev=threadtime();pwall=wall;
}
'''
i=s.index('bool Before(int fn, Call c)');s=s[:i]+pre+s[i:];k='}  // namespace';i=s.index(k,s.index('void TakeInit()'));s=s[:i]+native.read_text()+s[i:]
a='R32(c.r[ESP]) == 0x0030C0B2 ? c.r[ESP] : 0;'
assert s.count(a)==1
s=s.replace(a,a+'''
        if(trial){ ++idx;oldeligible+=!!captured_index_stack;
          if(!captured_index_stack && c.a(2) && c.a(1)>0 && c.a(0)>=1 && c.a(0)<=10){
            ++fresh;extraindices+=c.a(1);
            if(fast)captured_index_stack=c.r[ESP];
          }
        }''')
a='bool took = Before(fn, Call{regs});'
s=s.replace(a,a+'''
    if(fn==D3DF_D3DDevice_Swap)abflip();
    if(trial && fn==D3DF_D3DDevice_DrawVerticesUP)++up;
    if(trial && fn==D3DF_D3DDevice_DrawVertices){++linear;if(fast&&!took && native_linear(regs)){++linhit;return 1;}}
''')
output.write_text('#include <time.h>\n'+s)
