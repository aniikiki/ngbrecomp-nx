"""Cache exact 4x4 products inside three original calls made by 1D7810.
Preserve the original prologue, epilogue, FP slots and all due polls."""
from pathlib import Path
import sys,shlex,subprocess as sp
here=Path(__file__).resolve().parent;sys.path.insert(0,str(here.parents[1]/'perf'))
from native_probe import *
d=BASE/'core-perf/opening-setup'
if sys.argv[1]=='cross':
 s=(BASE/'gen/recomp_0039.c').read_text()
 k='void sub_0037A5C5(void)\n{'
 s=s.replace(k,'''extern unsigned om_arm,om_active,om_calls[3],om_same[3],om_hits[3];
struct MatSlot { unsigned valid,ctrl,top; unsigned char left[64],right[64],product[64]; double fp[8];};
static struct MatSlot om_slots[3];
'''+k+'''
    struct MatSlot *os=NULL; unsigned oi=0,compare=0;
    unsigned char *od=NULL;
''')
 k='loc_0037A649: ;';z=s.index(k);i=s.index('loc_0037A657:',z)
 s=s[:i]+'''    if(om_active && om_arm){
        unsigned ret=MEM32(ebp+4);
        if(ret==0x1d7917 || ret==0x1d792b || ret==0x1d794e){
          oi=ret==0x1d7917?0:ret==0x1d792b?1:2;
          const void *l=ngb_ram_span(ecx,64),*r=ngb_ram_span(edx,64);
          od=ngb_ram_span(ebx,64);
          // Only ordinary disjoint output. No guest writes/readbacks or IRQ can intervene.
          if(l && r && od && ((uintptr_t)od+64<=(uintptr_t)l || (uintptr_t)l+64<=(uintptr_t)od)
           && ((uintptr_t)od+64<=(uintptr_t)r || (uintptr_t)r+64<=(uintptr_t)od)){
            struct MatSlot *v=&om_slots[oi];
            ++om_calls[oi];
            unsigned equal=v->valid && v->ctrl==g_fp_control_word && v->top==g_fp_top &&
              !memcmp(v->left,l,64) && !memcmp(v->right,r,64);
            om_same[oi]+=equal;
            if(ngb_poll_mask>=20 && !(ngb_poll_mask&(ngb_poll_mask+1)) && !ngb_pending_dpcs &&
               (ngb_guest_polls & ngb_poll_mask)<=ngb_poll_mask-20){
              os=v;
              if(equal && om_arm){
                ++om_hits[oi];
                if(om_arm==2)compare=1;
                else {
                  memcpy(od,v->product,64); memcpy(g_fp_stack,v->fp,64);
                  ecx+=64;ngb_guest_polls+=20;goto loc_0037A6A1;
                }
              }
              if(!compare){os->valid=0;os->ctrl=g_fp_control_word;os->top=g_fp_top;
                memcpy(os->left,l,64);memcpy(os->right,r,64);}
            }
          }
        }
    }
'''+s[i:]
 k='loc_0037A6A1: ;'
 s=s.replace(k,k+'''
    if(os && (compare || !os->valid)){
      if(compare && (memcmp(os->product,od,64)||memcmp(os->fp,g_fp_stack,64)||os->top!=g_fp_top))__builtin_trap();
      memcpy(os->product,od,64);memcpy(os->fp,g_fp_stack,64);os->valid=1;
    }
''')
 f=d/'matrix.c';f.write_text(s)
 c=next(shlex.split(x) for x in sp.check_output(['ninja','-t','commands','ngb-startup'],cwd=BASE/'switch',text=True).splitlines() if x.endswith('/recomp_0039.c'))
 c[c.index('-o')+1]=str(f)+'.o';c[c.index('-MF')+1]=str(f)+'.d';c[-1]=str(f);c.insert(-1,'-g0');sp.run(c,cwd=BASE/'switch',check=True)
else:
 p=NativeProbe('opening-setup');p.driver('''
unsigned om_arm,om_active,om_calls[3],om_same[3],om_hits[3];
void om_frame(unsigned f,unsigned draws){
 static uint64_t last;static unsigned prev;
 struct timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);uint64_t now=(uint64_t)t.tv_sec*1000000000+t.tv_nsec;
 if(f && last)fprintf(stderr,"[OPEN_PAIR] %u %u %llu %u\\n",f,om_arm,(unsigned long long)(now-last),draws-prev);
 if(f==120)for(unsigned i=0;i<3;i++)fprintf(stderr,"[MATRIX] %u %u %u %u\\n",i,om_calls[i],om_same[i],om_hits[i]);
 om_arm=getenv("NGB_OPEN_CHECK")?2:(((f/2+12345)*2654435761u>>31)^(f&1)^(getenv("NGB_OPEN_REVERSE")!=NULL));
 om_active=f<120;last=now;prev=draws;
}
''')
 p.link[next(i for i,v in enumerate(p.link) if v.endswith('/recomp_0039.o'))]=str(d/'matrix.c.o')
 s=(RUNTIME/'scene/bridge.c').read_text()
 for k,arg in [('            ngb_direct_reset_stats();','0'),('    ++scene_flips;','scene_flips')]:
  s=s.replace(k,k+f' extern void om_frame(unsigned,unsigned);om_frame({arg},draws);')
 p.add('scene/bridge.c',s);p.link.insert(1,'-Wl,--strip-debug');p.finish()
