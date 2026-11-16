"""One fixed 8-byte descriptor -> one content-validated state, no hash,
inversion or repeated validation of each previous actor. Only plain pool
inputs disjoint from every write take this path."""
from pathlib import Path
import textwrap
here=Path(__file__).resolve().parent;p=Path('/work/build/switch-runtime')
d=p/'opt050/contact-compact';d.mkdir(exist_ok=True)
s=(p/'opt050/contact-batch/fast.c').read_text()
a=s.index('/* Host shadow only:');b=s.index('static inline unsigned contact_group',a)
s=s[:a]+'''
struct contact_bounds {unsigned key,valid;unsigned char bytes[160];float m[3][4],box[7];};
static struct contact_bounds contact_cache[256];
static inline int simple_plain(uint32_t x,unsigned n){
    return x>=0x1000000u && x<0x3e00000u && (x&4095)+n<=ngb_fast_page_bytes[x>>12];
}
static inline int compact_miss(unsigned idx,unsigned desc,const float*ball,unsigned owner,unsigned st){
 unsigned actor=0x4b4e50+MEM8(desc)*0x2800u,boneid=MEM16(desc-2),box=MEM32(desc-6);
 if(actor>=0x7a0000 || boneid>=31 || box<0x84000000u || box>0x88000000u-64 || (box&4095)>4096-44 || ngb_fast_page_bytes[box>>12]<(box&4095)+44)return 0;
 unsigned bone=actor+(3+boneid)*64;
 // owner and ball are restricted to low ordinary VM; box to disjoint
 // physical backing above 64 MiB. The stack was separately checked.
 struct contact_bounds* c=&contact_cache[idx];
 unsigned char bytes[160];memcpy(bytes,ngb_fast_ram+actor,64);memcpy(bytes+64,ngb_fast_ram+actor+0x8c0,12);memcpy(bytes+76,ngb_fast_ram+bone,64);
 float bounds[7];memcpy(bounds,ngb_fast_ram+(box&0x7fffffffu)+16,28);
 if(c->key!=bone || !c->valid || memcmp(c->bytes,bytes,140)||memcmp(c->box,bounds,28)){
    float left[4][4],a[4][4],m[4][4];memcpy(left,bytes+76,64);memcpy(a,bytes,64);memcpy(a[3],bytes+64,12);
    for(int i=0;i<4;i++)for(int j=0;j<4;j++)m[i][j]=((left[i][0]*a[0][j]+left[i][1]*a[1][j])+left[i][2]*a[2][j])+left[i][3]*a[3][j];
    for(unsigned i=0;i<3;i++){
      for(unsigned j=0;j<3;j++)c->m[i][j]=m[i][j];
      c->m[i][3]=((0.f-m[3][0])*m[i][0]+(0.f-m[3][1])*m[i][1])+(0.f-m[3][2])*m[i][2];}
    memcpy(c->bytes,bytes,140);memcpy(c->box,bounds,28);c->valid=1;c->key=bone;
 }
 const float radius=ball[3]+MEMF(0x4149c4);
 for(int i=0;i<3;i++){
   float* m=c->m[i];
   float v=((ball[0]*m[0]+m[3])+ball[1]*m[1])+ball[2]*m[2];
   float delta=c->box[i]-v;
   if(0.f>(c->box[4+i]+delta)+radius || delta-radius>0.f)return 1;
 }
 return 0;
}
'''+s[b:]
a=s.index(' for(;n<capacity;n++){');b=s.index(' if(n<2)',a)
s=s[:a]+'''
 if(!simple_plain(actor_query,40))return 0;
 unsigned ball=MEM32(actor_query);
 if(!simple_plain(ball,16) || (ball<sp+112 && ball+16>sp-256) ||
    (actor_query<sp+112 && actor_query+40>sp-256))return 0;
 float xyz[4];memcpy(xyz,ngb_fast_ram+ball,16);
 for(;n<capacity;n++)if(!compact_miss(i+n,node+8*n,xyz,actor_query,sp))break;
'''+s[b:]
s=s.replace("if(!simple_plain(actor_query,40))return 0;", "if(!simple_plain(actor_query,40) && !(actor_query>=0x10000 && actor_query<0x1000000-40 && (actor_query<0x4b4e50 || actor_query>0x7a9000) && !(actor_query<0x9501c0 && actor_query+40>0x950180) && !(actor_query<0xdb67c4 && actor_query+40>0xdb67c0)))return 0;")
(d/'fast.c').write_text(s)
q=(here/'leaf.py').read_text();q=textwrap.dedent(q[q.index(" abi=Path('/work/packaging/switch/arm-registers')"):]).replace('opt050/contact-leaf','opt050/contact-compact');exec(q)
