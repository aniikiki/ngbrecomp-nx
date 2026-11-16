"""Opening experiment: compare the two material pieces directly, emitting original spans."""
def transform(text):
    k='        if (!std::memcmp(previous, now + r.off, r.len)) return;'
    assert text.count(k)==1
    return '#include <cstdlib>\nstatic const bool material_control=std::getenv("NGB_MATERIAL_CONTROL")!=nullptr;\n'+text.replace(k,'''        if constexpr(r.off==offsetof(State,material)) {
            static_assert(r.len==68 && kPiece==64);
            if(!material_control){
                bool head=std::memcmp(previous,now+r.off,64)!=0;
                bool tail=std::memcmp(previous+64,now+r.off+64,4)!=0;
                if(head) WriteDelta(r.off,now,tail?68:64);
                else if(tail) WriteDelta(r.off+64,now,4);
                return;
            }
        }
'''+k)
