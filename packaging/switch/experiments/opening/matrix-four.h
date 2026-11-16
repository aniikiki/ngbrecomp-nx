/* Enter immediately after the first outer poll. The remaining three outer
 * and sixteen inner polls have no observable callback on this fast path. */
static inline bool ngb_matrix_four(uint32_t left,uint32_t right,uint32_t dest){
 uint64_t ticket=ngb_guest_polls;unsigned mask=ngb_poll_mask;
 if(ngb_pending_dpcs||mask<19||(mask&(mask+1u))||(ticket&mask)>mask-19||
    (g_fp_control_word&0x300u))return false;
 if((left|right|dest)&3u)return false;
 const float *l=ngb_ram_span(left,64),*r=ngb_ram_span(right,64);
 float *d=ngb_ram_span(dest,64);
 if(!l||!r||!d)return false;
 uintptr_t x=(uintptr_t)d,y=(uintptr_t)l,z=(uintptr_t)r;
 if((x<y+64 && y<x+64)||(x<z+64 && z<x+64))return false;
 float32x4x4_t a=vld1q_f32_x4(l),b=vld1q_f32_x4(r);
 uint32x4_t ok=vdupq_n_u32(~0u);
 for(unsigned i=0;i<4;i++)ok=vandq_u32(ok,vandq_u32(ngb_arm_dot_range(a.val[i]),ngb_arm_dot_range(b.val[i])));
 if(!vminvq_u32(ok))return false;
 unsigned t=g_fp_top;
 for(unsigned i=0;i<4;i++){
  float32x4_t k=a.val[i],p0=vmulq_laneq_f32(b.val[0],k,0),p1=vmulq_laneq_f32(b.val[1],k,1);
  float32x4_t p2=vmulq_laneq_f32(b.val[2],k,2),p3=vmulq_laneq_f32(b.val[3],k,3);
  float32x4_t odd=vaddq_f32(p1,p3),v=vaddq_f32(vaddq_f32(p2,p0),odd);
  vst1q_f32(d+4*i,v);
  if(i==3){
   /* Four pushes per row, with the same eight physical x87 slots reused. */
   g_fp_stack[t]=vgetq_lane_f32(k,3);g_fp_stack[(t+1)&7]=vgetq_lane_f32(k,2);
   g_fp_stack[(t+2)&7]=vgetq_lane_f32(k,1);g_fp_stack[(t+3)&7]=vgetq_lane_f32(k,0);
   g_fp_stack[(t+4)&7]=vgetq_lane_f32(p0,3);g_fp_stack[(t+5)&7]=vgetq_lane_f32(p3,3);
   g_fp_stack[(t+6)&7]=vgetq_lane_f32(odd,3);g_fp_stack[(t+7)&7]=vgetq_lane_f32(v,3);
  }
 }
 ngb_guest_polls=ticket+19;return true;
}
