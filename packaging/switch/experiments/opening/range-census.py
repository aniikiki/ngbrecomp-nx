"""Observe the existing whole-range equality result without an extra compare."""
def transform(s):
    k='        if (!std::memcmp(previous, now + r.off, r.len)) return;'
    assert s.count(k)==1
    return 'extern "C" void range_observe(unsigned,unsigned,unsigned);\n'+s.replace(k,"        const bool equal=!std::memcmp(previous,now+r.off,r.len);\n        range_observe(I,r.len,equal);\n        if(equal)return;")
