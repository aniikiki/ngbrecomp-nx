    // On entry the enclosing fixed range is already known to differ.
    template<size_t N>
    void ChangedGroup(size_t off, const uint8_t* now) {
        static_assert(N>0 && N<=4*kPiece);
        const uint8_t* old=reinterpret_cast<const uint8_t*>(&sent_);
        if constexpr (N<=kPiece) { WriteDelta(off,now,N); }
        else {
            size_t first=0;
            auto piece=[&](size_t start, auto length) {
                constexpr size_t len=decltype(length)::value;
                if (!std::memcmp(old+off+start,now+off+start,len)) {
                    if(first<start) WriteDelta(off+first,now,start-first);
                    first=start+len;
                }
            };
            piece(0,std::integral_constant<size_t,kPiece>{});
            piece(kPiece,std::integral_constant<size_t,std::min(kPiece,N-kPiece)>{});
            if constexpr(N>2*kPiece) piece(2*kPiece,std::integral_constant<size_t,std::min(kPiece,N-2*kPiece)>{});
            if constexpr(N>3*kPiece) piece(3*kPiece,std::integral_constant<size_t,N-3*kPiece>{});
            if(first<N) WriteDelta(off+first,now,N-first);
        }
    }
    template<size_t I>
    void ChangedFixedRange(const uint8_t* now) {
        constexpr Range r=kStateRanges[I];
        constexpr size_t G=4*kPiece;
        const auto* old=reinterpret_cast<const uint8_t*>(&sent_);
        if constexpr(r.len<=G) ChangedGroup<r.len>(r.off,now);
        else {
            for(size_t i=0;i<r.len/G;i++) {
                const size_t off=r.off+i*G;
                if(std::memcmp(old+off,now+off,G)) ChangedGroup<G>(off,now);
            }
            if constexpr(r.len%G!=0) {
                constexpr size_t off=r.off+r.len/G*G;
                if(std::memcmp(old+off,now+off,r.len%G)) ChangedGroup<r.len%G>(off,now);
            }
        }
    }
