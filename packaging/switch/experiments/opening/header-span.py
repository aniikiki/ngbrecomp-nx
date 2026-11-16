"""Resolve ordinary headers once. Keep the original fallback and record length."""
def transform(s):
    a=s.index('        uint32_t type = kernel::R32(header)');b=s.index('        Recent&',a)
    old=s[a:b]
    assert old.count('kernel::HostPtr(header)')==1
    new='''#ifdef NGB_DIRECT3D
        if (const auto* p = static_cast<const uint8_t*>(DirectPage(header,20))) {
            std::memcpy(now.w,p,12);
            const uint32_t type=now.w[0]&0x70000;
            if(type>=0x20000 && type!=0x30000) std::memcpy(now.w+3,p+12,8);
        } else
#endif
        {
'''+old+'        }\n'
    return s[:a]+new+s[b:]
