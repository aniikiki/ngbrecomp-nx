// Compare 64-byte pieces once. Preserve the original 256-byte command boundaries.
        if constexpr(r.off==offsetof(State,rs)){
            static_assert(r.len==1336);
            if(dm_mode){
                uint32_t mask=0;constexpr unsigned pieces=(r.len+63)/64;
                for(unsigned i=0;i<pieces-1;i++){
                    const auto *a=previous+i*64,*b=now+r.off+i*64;
                    auto diff=veorq_u8(vld1q_u8(a),vld1q_u8(b));
                    for(unsigned j=16;j<64;j+=16)diff=vorrq_u8(diff,veorq_u8(vld1q_u8(a+j),vld1q_u8(b+j)));
                    if(vmaxvq_u8(diff))mask|=1u<<i;
                }
                if(std::memcmp(previous+64*(pieces-1),now+r.off+64*(pieces-1),r.len%64))mask|=1u<<(pieces-1);
                if(dm_mode==2){
                    for(unsigned i=0;i<pieces;i++){
                        bool ref=std::memcmp(previous+i*64,now+r.off+i*64,std::min(size_t(64),r.len-i*64))!=0;
                        if(ref!=bool(mask&(1u<<i)))std::abort();
                    }
                    ++dm_checked;if(mask)++dm_changed;
                }else {
                    while(mask){
                        unsigned i=__builtin_ctz(mask),end=i+1;
                        while((end&3) && (mask&(1u<<end)))++end;
                        size_t len=std::min(size_t(end*64),r.len)-i*64;
                        WriteDelta(r.off+i*64,now,len);
                        mask&=~(((1u<<(end-i))-1)<<i);
                    }
                    return;
                }
            }
        }
