"""Count opportunities for coalescing records across a short unchanged byte gap, only within one State command."""
def transform(s):
    a='        size_t first = cur_->bytes.size();'
    b='    void WriteDelta(size_t off, const uint8_t* now, size_t bytes) {'
    assert s.count(a)==s.count(b)==1
    return '#include <stddef.h>\nextern "C" void gap_reset();\nextern "C" void gap_write(size_t,size_t);\n'+s.replace(a,a+'\n        gap_reset();').replace(b,b+'\n        gap_write(off,bytes);')
