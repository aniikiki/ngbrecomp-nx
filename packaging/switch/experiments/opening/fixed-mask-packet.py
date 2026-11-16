"""Encode changed fixed state ranges once, with one mask and one allocation per Draw.
Other ranges and pointer lifetimes retain the existing state-command encoding."""
def transform(t):
    def once(a,b):
        nonlocal t
        assert t.count(a)==1,a
        t=t.replace(a,b)
    k='    // what changed since the last command'
    once(k,'''    template<size_t... I>
    void PackFixed(const uint8_t* now, Cmd& c, std::index_sequence<I...>) {
        static_assert(sizeof...(I) <= 32);
        auto* sent = reinterpret_cast<uint8_t*>(&sent_);
        size_t n = 0;
        auto mark = [&](auto index) {
            constexpr size_t i=decltype(index)::value;
            constexpr Range r=kStateRanges[i];
            if(std::memcmp(now+r.off,sent+r.off,r.len)){
                c.c |= uint32_t{1}<<i; n+=r.len;
            }
        };
        (mark(std::integral_constant<size_t,I>{}),...);
        if(!n) return;
        size_t at=cur_->bytes.size();
        cur_->bytes.resize(at+n);
        uint8_t* out=cur_->bytes.data()+at;
        auto put = [&](auto index) {
            constexpr size_t i=decltype(index)::value;
            constexpr Range r=kStateRanges[i];
            if(c.c & (uint32_t{1}<<i)){
                std::memcpy(out,now+r.off,r.len);
                std::memcpy(sent+r.off,now+r.off,r.len);
                out+=r.len;
            }
        };
        (put(std::integral_constant<size_t,I>{}),...);
    }
    template<size_t... I>
    static const uint8_t* UnpackFixed(uint32_t mask,const uint8_t* p,uint8_t* state,std::index_sequence<I...>){
        auto put=[&](auto index){
            constexpr size_t i=decltype(index)::value;
            constexpr Range r=kStateRanges[i];
            if(mask & (uint32_t{1}<<i)){std::memcpy(state+r.off,p,r.len);p+=r.len;}
        };
        (put(std::integral_constant<size_t,I>{}),...);
        return p;
    }
'''+k)
    once('SendFixedRanges(now, std::make_index_sequence<kStateRanges.size()>{});','PackFixed(now,c,std::make_index_sequence<kStateRanges.size()>{});')
    once('for (const uint8_t* p = data; p < data + c.size;)','for (const uint8_t* p = UnpackFixed(c.c,data,s,std::make_index_sequence<kStateRanges.size()>{}); p < data + c.size;)')
    return t
