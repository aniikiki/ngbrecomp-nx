"""Remember a previously changed word as a cheap proof of inequality only."""
def transform(s):
    k='    template<size_t I>\n    void SendFixedRange'
    assert s.count(k)==1
    s=s.replace(k,'    size_t witness_[kStateRanges.size()]{};\n'+k)
    k='        if (!std::memcmp(previous, now + r.off, r.len)) return;'
    assert s.count(k)==1
    s=s.replace(k,'''        if constexpr(r.len>=128){
            size_t w=witness_[I];
            if(!std::memcmp(previous+w,now+r.off+w,4)){
                if(!std::memcmp(previous,now+r.off,r.len))return;
            }
            active_witness_=&witness_[I];witness_base_=r.off;witness_len_=r.len;
        } else if (!std::memcmp(previous, now+r.off,r.len)) return;''')
    k='        else SendRange(now, r);';assert s.count(k)==1
    s=s.replace(k,k+'\n        if constexpr(r.len>=128) active_witness_=nullptr;')
    k='    void WriteDelta(size_t off, const uint8_t* now, size_t bytes) {';assert s.count(k)==1
    return s.replace(k,'    size_t *active_witness_=nullptr;size_t witness_base_=0,witness_len_=0;\n'+k+'''
        if(active_witness_ && bytes>=4 && off>=witness_base_ && off-witness_base_<=witness_len_-4){
            auto old=reinterpret_cast<const uint8_t*>(&sent_)+off;
            for(size_t j=0;j+4<=std::min(bytes,size_t(64));j+=4){
                if(std::memcmp(old+j,now+off+j,4)){
                    *active_witness_=off-witness_base_+j;break;
                }
            }
        }''')
