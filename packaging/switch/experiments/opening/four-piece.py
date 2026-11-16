"""Classify all four 64-byte pieces in one pass, with one vector-to-scalar read."""
def transform(s):
 k='            if (group > kPiece && !std::memcmp'
 assert s.count(k)==1
 p='''
            if(group==256 && !four_piece_control){
                unsigned changed=four_piece_mask(sent+off,now+off);
                if(four_piece_verify){
                    unsigned expected=0;
                    for(unsigned j=0;j<4;j++) expected|=(std::memcmp(sent+off+64*j,now+off+64*j,64)!=0)<<j;
                    if(changed!=expected)std::abort();
                    if((++four_piece_checks%65536)==0)std::fprintf(stderr,"[FOUR_PIECE] %llu\\n",four_piece_checks);
                }
                for(unsigned bits=changed;bits;){
                    unsigned first=__builtin_ctz(bits),last=first+1;
                    while(bits&(1u<<last))++last;
                    WriteDelta(off+64*first,now,64*(last-first));
                    bits&=~(((1u<<(last-first))-1u)<<first);
                }
                off+=256;continue;
            }
'''
 header='''#include <arm_neon.h>
#include <cstdio>
#include <cstdlib>
static bool four_piece_control=std::getenv("NGB_FOUR_CONTROL")!=nullptr;
static bool four_piece_verify=std::getenv("NGB_FOUR_VERIFY")!=nullptr;
static thread_local unsigned long long four_piece_checks;
static inline uint8x16_t four_piece_diff(const uint8_t* a,const uint8_t* b){
 auto x=veorq_u8(vld1q_u8(a),vld1q_u8(b));
 auto y=veorq_u8(vld1q_u8(a+16),vld1q_u8(b+16));
 auto z=veorq_u8(vld1q_u8(a+32),vld1q_u8(b+32));
 auto w=veorq_u8(vld1q_u8(a+48),vld1q_u8(b+48));
 return vorrq_u8(vorrq_u8(x,y),vorrq_u8(z,w));
}
static inline unsigned four_piece_mask(const uint8_t* a,const uint8_t* b){
 auto d0=four_piece_diff(a,b), d1=four_piece_diff(a+64,b+64);
 auto d2=four_piece_diff(a+128,b+128),d3=four_piece_diff(a+192,b+192);
 auto v=vpmaxq_u8(vpmaxq_u8(d0,d1),vpmaxq_u8(d2,d3));
 auto eq=vceqq_u32(vreinterpretq_u32_u8(v),vdupq_n_u32(0));
 const uint32_t weights[4]={1,2,4,8};
 return vaddvq_u32(vbicq_u32(vld1q_u32(weights),eq));
}
'''
 return header+s.replace(k,p+k)
