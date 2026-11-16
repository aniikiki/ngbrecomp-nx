"""Measure where indices actually compared with cached snapshots originate."""
from pathlib import Path
import struct
def transform(t):
 k='        if (slot.snapshot && !std::memcmp(slot.snapshot->bytes.data(), src, bytes)) {'
 assert t.count(k)==1
 return 'extern "C" void io_compare(const void*, unsigned);\n'+t.replace(k,'        if(slot.snapshot)io_compare(src,bytes);\n'+k)
def tag_hle(s):
 k='if (c.a(2)) Draw(c.a(0), 0, c.a(1), static_cast<const uint8_t*>(HostPtr(c.a(2))));'
 assert s.count(k)==1
 return 'extern "C" void io_tag(const void*,unsigned);\n'+s.replace(k,'if(auto va=c.a(2)){ auto p=static_cast<const uint8_t*>(HostPtr(va)); io_tag(p,va); Draw(c.a(0),0,c.a(1),p); io_tag(nullptr,0); }')
def counters():
 b=Path('game_files/default.xbe').read_bytes();u=lambda o:struct.unpack_from('<I',b,o)[0]
 base=u(0x104);n=u(0x11c);a=u(0x120)-base
 assert b[:4]==b'XBEH' and 0<n<128 and a+56*n<=len(b)
 sections=[]
 for i in range(n):
  flags,va,size=struct.unpack_from('<III',b,a+i*56)
  assert va+size<=2**32
  sections.append('{%du,%du,%du}'%(va,va+size,flags&1))
 return r"""
static const struct {unsigned lo,hi,writable;} io_sec[]={SECTIONS};
static _Thread_local unsigned io_on;
static _Thread_local unsigned long long io_n[4],io_bytes[4];
static _Thread_local const void *io_p;
static _Thread_local unsigned io_va;
static _Thread_local unsigned long long io_cnt[6],io_size[6];
void io_tag(const void *p,unsigned va){io_p=p;io_va=va;}
void io_compare(const void *ptr,unsigned bytes){
 if(!io_on)return;
 uintptr_t delta=(uintptr_t)ptr-(uintptr_t)ngb_fast_ram;
 unsigned kind=3;
 if(delta<0x4000000 && bytes<=0x4000000-delta){
  kind=2;
  for(unsigned i=0;i<sizeof io_sec/sizeof io_sec[0];i++)if(delta>=io_sec[i].lo&&delta+bytes<=io_sec[i].hi){kind=io_sec[i].writable;break;}
 }
 unsigned g=5;
 if(io_p==ptr){
  g=io_va<0x4000000?2:io_va>=0x80000000&&io_va<0x88000000?3:4;
  for(unsigned i=0;i<sizeof io_sec/sizeof io_sec[0];i++)
   if(io_va>=io_sec[i].lo&&(uint64_t)io_va+bytes<=io_sec[i].hi){g=io_sec[i].writable;break;}
 }
 io_cnt[g]++;io_size[g]+=bytes;
 io_n[kind]++;io_bytes[kind]+=bytes;
}
void phase_flip(unsigned f){
 if(f==30||f==120)for(unsigned i=0;i<4;i++)fprintf(stderr,"[INDEX_ORIGIN] %u %u %llu %llu\n",f,i,io_n[i],io_bytes[i]);
 if(f==30||f==120)for(unsigned i=0;i<6;i++)fprintf(stderr,"[INDEX_TAG] %u %u %llu %llu\n",f,i,io_cnt[i],io_size[i]);
 if(!f||f==30){memset(io_cnt,0,sizeof io_cnt);memset(io_size,0,sizeof io_size);memset(io_n,0,sizeof io_n);memset(io_bytes,0,sizeof io_bytes);}
 io_on=f<120;
}
""".replace('SECTIONS',','.join(sections))
