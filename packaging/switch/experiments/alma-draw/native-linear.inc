// Offline comparison: HLE already submitted this draw. Native equivalent of
// XDK DrawVertices' no-refill path. Preserve the complete guest FIFO packet.
static bool native_linear(uint32_t* r) {
    uint32_t sp=r[ESP], n=r[EAX], start=r[ECX], dev=R32(kDevicePtr);
    if (!g_take[D3DF_CDevice_SetStateVB] || !dev || n==0 || n>65536 ||
        sp<28 || ((dev|sp)&3)) return false;
    uint32_t batches=(n+255)/256, bytes=20+4*batches;
    uint32_t put=R32(dev), limit=R32(dev+4);
    if ((put&3) || uint64_t(put)+bytes >= uint64_t(limit)+512 ||
        limit>UINT32_MAX-512 || put>UINT32_MAX-bytes) return false;
    auto* pkt=const_cast<uint32_t*>(static_cast<const uint32_t*>(DirectPage(put,bytes)));
    auto* stk=const_cast<uint32_t*>(static_cast<const uint32_t*>(DirectPage(sp-28,36)));
    auto* dp=const_cast<uint32_t*>(static_cast<const uint32_t*>(DirectPage(dev,8)));
    if (!pkt || !stk || !dp) return false;
    auto overlaps=[](const void* a,unsigned an,const void* b,unsigned bn) {
        auto x=reinterpret_cast<uintptr_t>(a),y=reinterpret_cast<uintptr_t>(b);
        return x<y+bn && y<x+an;
    };
    if(overlaps(pkt,bytes,stk,36)||overlaps(dp,8,stk,36)||overlaps(dp,8,pkt,bytes))return false;
    uint32_t prim=stk[8];
    stk[0]=0x003C9A86;stk[1]=dev;stk[2]=0;stk[3]=r[EDI];stk[4]=r[ESI];
    stk[5]=r[EBP];stk[6]=r[EBX];
    pkt[0]=0x417fc;pkt[1]=prim;pkt[2]=0x40001810+(batches<<18);
    for(unsigned i=0;i<batches;i++)pkt[3+i]=(start+i*256)|((std::min(n-i*256,256u)-1)<<24);
    pkt[3+batches]=0x417fc;pkt[4+batches]=0;
    dp[0]=put+bytes;r[EAX]=dp[0];r[ESP]=sp+8;
    r[ECX]=batches==1?limit+512:0;
    r[EDX]=batches==1?prim:((start+256*(batches-2))|0xff000000);
    return true;
}
