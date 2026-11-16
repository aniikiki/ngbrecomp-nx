"""Resolve one changed shader-constant range without rereading all unchanged blocks."""
def transform(s):
    k='void SyncDrawConstants() {'
    assert s.count(k)==1 and s.count('gpu::SyncConstantRange<')==3
    impl='''
template<unsigned First,unsigned Count,unsigned Block>
static inline uint32_t ResolveDifferent(uint8_t* dst,const uint8_t* src) {
    if constexpr(Count==1){
        std::memcpy(dst+First*Block,src+First*Block,Block);
        return 1u<<First;
    }else{
        constexpr unsigned left=Count/2,right=Count-left;
        if(!std::memcmp(dst+First*Block,src+First*Block,left*Block))
            return ResolveDifferent<First+left,right,Block>(dst,src);
        uint32_t mask=ResolveDifferent<First,left,Block>(dst,src);
        if(std::memcmp(dst+(First+left)*Block,src+(First+left)*Block,right*Block))
            mask |= ResolveDifferent<First+left,right,Block>(dst,src);
        return mask;
    }
}
template<unsigned First,unsigned Count,unsigned Block>
static inline uint32_t SyncGroups(uint8_t* dst,const uint8_t* src){
    if(!std::memcmp(dst+First*Block,src+First*Block,Count*Block))return 0;
    return ResolveDifferent<First,Count,Block>(dst,src);
}
'''
    return s.replace(k,impl+k).replace('gpu::SyncConstantRange<','SyncGroups<')
