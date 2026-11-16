from pathlib import Path
import tempfile,subprocess,runpy
p=Path(__file__).parent
rt=p.parents[1]/'runtime'
s=(rt/'timers.c').read_text()
t=runpy.run_path(str(p/'timer-mask.py'))['transform'](s)
driver=r'''
#include "timers.h"
#include <stdio.h>
#include <assert.h>
static unsigned h=31,n;static uint64_t tick;
static void fire(uint32_t a,uint32_t d,int period){
 h=h*16777619u+a+d+(unsigned)period; n++;
 unsigned k=(a*7+d)%32+1;
 if((d&3)==1)ngb_timer_arm(k,tick,0,0,d+1);
 if((d&3)==2)ngb_timer_cancel(k);
 if((d&3)==3)ngb_timer_initialize(k);
}
int main(){unsigned x=2;
for(unsigned pass=0;pass<100;pass++){
 ngb_timers_reset();for(unsigned i=1;i<=32;i++)assert(!ngb_timer_initialize(i));
 for(unsigned j=0;j<4000;j++){
 x=x*1664525u+1013904223u;unsigned a=1+(x>>16)%32;tick=(j==3999)?UINT64_MAX:j;
 if(x&1)h+=ngb_timer_arm(a,tick,(x>>10)%9,(x>>7)%3,x>>3);
 else if(x&2)h+=ngb_timer_cancel(a);else ngb_timer_initialize(a);
 ngb_timers_poll(tick,fire);
 }}
printf("%u %u\n",n,h);}
'''
with tempfile.TemporaryDirectory() as td:
 q=Path(td);f=q/'timer.c';e=q/'test';main=q/'driver.c';main.write_text(driver);outputs=[]
 for text in (s,t):
    f.write_text(text)
    for d in (rt/'timers_test.c',main):
        subprocess.run(['cc','-O2','-I'+str(rt),f,d,'-o',e],check=True)
        out=subprocess.check_output([e])
    outputs.append(out)
 assert outputs[0]==outputs[1] and int(outputs[0].split()[0])>1000,outputs
 print('400000 polls, matching callback stream:',out.decode().strip())
