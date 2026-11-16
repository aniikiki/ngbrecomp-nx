// Only admit a single packed index packet; index payloads are never cached.
// Check every command word and the end marker afresh; payload remains live.
static bool direct_packet(uint32_t data,uint32_t size,uint32_t &prim,uint32_t &count,const uint8_t *&ptr){
 if(size<24 || (size&3) || size>65536 || data<0x84000000u || data>0x88000000u-size)return false;
 for(unsigned page=data>>12;page<=(data+size-1)>>12;++page)
   if(ngb_fast_page_bytes[page]!=4096 || ngb_target_pages[page&32767])return false;
 auto src=ngb_fast_ram+(data&0x7fffffff);
 auto word=[&](unsigned i){uint32_t v;std::memcpy(&v,src+4*i,4);return v;};
 const unsigned n=size/4;
 if(word(0)!=0x417fc || !(prim=word(1)))return false;
 unsigned h=word(2),nw=(h>>18)&2047;
 if((h&~(0x1ffc0000u|0x40000000u))!=0x1800 || !nw || nw>n-3)return false;
 unsigned i=3+nw;
 if(i<n && word(i)==0x417fc){if(i+1>=n||word(i+1))return false;i+=2;}
 if(i!=n && !(i+1==n && ((word(i)&3)==1 || (word(i)&0xe0000003)==0x20000000)))return false;
 ptr=src+12;count=2*nw;return true;
}
