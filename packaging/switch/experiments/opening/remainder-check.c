// Check partitioning including a fiber handoff inside material and a frame split.
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
static unsigned long long tick;
static uint64_t ngb_elapsed_ns(void){return tick;}
static void ngb_kernel_log(const char *s){(void)s;}
static struct{unsigned mesh_depth,index_depth,material_depth;uint64_t edge,other_ns;}index_time;
static unsigned ngb_direct_detail_frame=1;
#include "remainder-clock.inc"
static uint64_t val(unsigned k,unsigned g){for(unsigned j=2;j<RB_N;j++)if(rb[j].used&&rb[j].key==k)return rb[j].ns[g];return 0;}
int main(void){
 rb_start();tick=3;ngb_rb_set(10);tick=8;rb_tick(tick);index_time.mesh_depth=1;
 tick=20;ngb_rb_set(11);tick=22;rb_tick(tick);index_time.mesh_depth=0;
 tick=24;rb_tick(tick);index_time.material_depth=1;tick=30;ngb_rb_set(10);
 tick=32;rb_tick(tick);index_time.material_depth=0;tick=35;rb_tick(tick);
 index_time.other_ns=21;rb_finish(1);
 assert(rb[0].ns[0]==3 && val(10,0)==8 && val(11,0)==2 && rb[1].ns[0]==8);
 assert(rb_total[0]==21 && !rb_active && rb_group==1);
 return 0;
}
