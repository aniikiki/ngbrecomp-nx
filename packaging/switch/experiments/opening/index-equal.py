"""Exact equality for the repeated immutable index snapshot path, AArch64."""
body=r'''
static inline bool index_bytes_equal(const uint8_t* a,const uint8_t* b,size_t n){
    while(n>=64){
        uint8x16_t d0=veorq_u8(vld1q_u8(a),vld1q_u8(b));
        uint8x16_t d1=veorq_u8(vld1q_u8(a+16),vld1q_u8(b+16));
        uint8x16_t d2=veorq_u8(vld1q_u8(a+32),vld1q_u8(b+32));
        uint8x16_t d3=veorq_u8(vld1q_u8(a+48),vld1q_u8(b+48));
        if(vmaxvq_u8(vorrq_u8(vorrq_u8(d0,d1),vorrq_u8(d2,d3))))return false;
        a+=64;b+=64;n-=64;
    }
    return !n || !std::memcmp(a,b,n);
}
'''
def transform(s):
    k='!std::memcmp(slot.snapshot->bytes.data(), src, bytes)'
    assert s.count(k)==1 and s.count('struct IndexSnapshot {')==1
    return '#include <arm_neon.h>\n'+s.replace('struct IndexSnapshot {',body+'\nstruct IndexSnapshot {').replace(k,'index_bytes_equal(slot.snapshot->bytes.data(), src, bytes)')
