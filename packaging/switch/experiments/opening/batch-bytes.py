"""Retain initialized byte storage across batch recycling; preserve alignment padding."""
ARENA='''struct BatchBytes {
    std::vector<uint8_t> backing;
    size_t used = 0;
    size_t size() const { return used; }
    uint8_t* data() { return backing.data(); }
    const uint8_t* data() const { return backing.data(); }
    void resize(size_t n) {
        if (n > backing.size()) backing.resize(n);
        used = n;
    }
    void clear() { used = 0; }
};
'''
def transform(s):
    k='struct Batch {';assert s.count(k)==1
    a=s.index(k);b=s.index('\n};',a)
    key='std::vector<uint8_t> bytes;';assert s[a:b].count(key)==1
    s=s[:a]+ARENA+s[a:b].replace(key,'BatchBytes bytes;')+s[b:]
    k='        cur_->bytes.resize(at + n);';assert s.count(k)==1
    return s.replace(k,'        size_t previous=cur_->bytes.size();\n'+k+'\n        if (at != previous) std::memset(cur_->bytes.data()+previous,0,at-previous);')
