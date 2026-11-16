"""The Switch HLE stores pre-deferred simple states in simple[], not rs[0..91]."""
def threaded(s):
 k='        constexpr Range r = kStateRanges[I];'
 assert s.count(k)==1
 s=s.replace(k,'''        Range r = kStateRanges[I];
        if constexpr(I==6) {
            static_assert(kStateRanges[I].off==offsetof(State,rs));
            constexpr size_t prefix=4*kPiece;
            static_assert(prefix<=kRsDeferredFirst*sizeof(uint32_t));
            const bool trusted = now==ngb_opening_hle_state();
            if(trusted && rs_was_hle_) { r.off+=prefix; r.len-=prefix; }
            rs_was_hle_=trusted;
        }''')
 # Keep all other template instantiations compile-time sized and inlined.
 s=s.replace('if constexpr (r.len <= kPiece)','if constexpr (kStateRanges[I].len <= kPiece)')
 k='    template<size_t I>\n    void SendFixedRange'
 assert s.count(k)==1
 return ('extern "C" const void* ngb_opening_hle_state();\n'+s.replace(k,'    bool rs_was_hle_=false;\n'+k))
def hle(s):
 k='extern "C" int d3d_hle_call('
 assert s.count(k)==1
 return s.replace(k,'extern "C" const void* ngb_opening_hle_state(){return &g_state;}\n'+k)
