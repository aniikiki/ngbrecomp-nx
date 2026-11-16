"""Start object lifetimes without zero filling elements immediately overwritten by memcpy."""
allocator=r"""
template<class T> struct PushOverwriteAlloc : std::allocator<T> {
    using value_type=T;
    template<class U> struct rebind {using other=PushOverwriteAlloc<U>;};
    PushOverwriteAlloc()=default;
    template<class U> PushOverwriteAlloc(const PushOverwriteAlloc<U>&) {}
    template<class U> void construct(U* p){::new(static_cast<void*>(p)) U;}
    template<class U,class A,class... B> void construct(U* p,A&& a,B&&... b){
        ::new(static_cast<void*>(p)) U(std::forward<A>(a),std::forward<B>(b)...);
    }
};
"""
def transform(s):
 k='void RunPushBuffer(uint32_t pb) {'
 assert s.count(k)==1
 a=s.index(k);b=s.index('\n}',a);part=s[a:b]
 assert part.count('std::vector<uint16_t> idx;')==1
 assert part.count('idx.resize(')==1 and 'if (count) std::memcpy(idx.data() + first, v, size_t(count) * 4);' in part
 return s[:a]+allocator+part.replace('std::vector<uint16_t> idx;', 'std::vector<uint16_t,PushOverwriteAlloc<uint16_t>> idx;')+s[b:]
