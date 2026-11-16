// Exclusive wall-time ledger. Switch between buckets on task/fiber and scope edges.
// Use the identical timestamp as the original parent ledger on shared boundaries.
#define RB_N 256u
static struct { unsigned key, used; uint64_t ns[7]; } rb[RB_N];
static unsigned rb_key,rb_slot,rb_frame,rb_active,rb_group,rb_trans,rb_overflow;
static uint64_t rb_edge,rb_total[7];
static void rb_tick(uint64_t now){
 if(rb_active && !index_time.mesh_depth && !index_time.index_depth)
  rb[ index_time.material_depth ? 1u : rb_slot ].ns[rb_group]+=now-rb_edge;
 rb_edge=now;
}
unsigned ngb_rb_set(unsigned key){
 unsigned prev=rb_key;if(key==prev)return prev;
 if(rb_active){rb_tick(ngb_elapsed_ns());++rb_trans;}
 rb_key=key;
 unsigned i=2+(key*2654435761u% (RB_N-2));
 if(!key)i=0;
 else for(unsigned n=0;n<RB_N;n++){
  if(!rb[i].used || rb[i].key==key)break;
  if(n==RB_N-1){i=0;rb_overflow++;break;}
  if(++i==RB_N)i=2;
 }
 rb_slot=i;if(i){rb[i].key=key;rb[i].used=1;}return prev;
}
static void rb_start(void){
 for(unsigned i=0;i<RB_N;i++)memset(rb[i].ns,0,sizeof rb[i].ns);
 memset(rb_total,0,sizeof rb_total);rb_frame=1;rb_group=rb_trans=rb_overflow=0;
 rb_active=1;rb_edge=index_time.edge;
}
static void rb_finish(unsigned f){
 if(rb_frame!=f)return;
 if(ngb_direct_detail_frame && rb_group<7)
  rb_total[rb_group]=index_time.other_ns;
 if(f==120){
  char l[210];uint64_t all=0;
  for(unsigned g=0;g<7;g++){
   uint64_t sum=0;
   for(unsigned j=0;j<RB_N;j++)if(rb[j].ns[g]){
    sum+=rb[j].ns[g];snprintf(l,sizeof l,"3D scene [RB] slot=%u key=%08x ns=%llu",g,j==1?0xffffffffu:rb[j].key,(unsigned long long)rb[j].ns[g]);ngb_kernel_log(l);
   }
   all+=sum;snprintf(l,sizeof l,"3D scene [RB_SUM] slot=%u sum=%llu parent_cum=%llu",g,(unsigned long long)sum,(unsigned long long)rb_total[g]);ngb_kernel_log(l);
  }
  snprintf(l,sizeof l,"3D scene [RB_END] total=%llu parent=%llu transitions=%u overflow=%u",(unsigned long long)all,(unsigned long long)index_time.other_ns,rb_trans,rb_overflow);ngb_kernel_log(l);
 }
 rb_group+=ngb_direct_detail_frame!=0;rb_frame=f+1;rb_active=0;
}
