"""Offline candidate: join longer adjacent strips and keep queued snapshots immutable."""
def transform(t):
    def once(a,b):
        nonlocal t
        assert t.count(a)==1,a
        t=t.replace(a,b)
    once('indices && prev.d == 1 && prev.b == start','indices && (prev.d == 1 || prev.d == 2) && prev.b == start')
    once('count > 32 || prev.c < 3 || prev.c > 64','count > 4096 || prev.c < 3 || prev.c > 4096')
    once('if (end != cur_->bytes.size()) return false;', '''if (prev.d == 1 && end != cur_->bytes.size()) return false;
        const uint8_t* old = prev.d==2 ? cur_->index_snapshots[prev.size]->bytes.data()
                                       : cur_->bytes.data()+prev.data;''')
    once('auto a = bounds(cur_->bytes.data() + prev.data, prev.c);','auto a = bounds(old, prev.c);')
    once('unsigned padding = 2 + (prev.c & 1);','''if(prev.d==2){
            prev.data=Put(old,size_t(prev.c)*2);
            prev.d=1;
            prev.size=0;
        }
        unsigned padding = 2 + (prev.c & 1);''')
    once('cur_->bytes.resize(end + 2*(padding + count));','cur_->bytes.resize(size_t(prev.data)+2*(prev.c+padding+count));')
    once('auto* dest = cur_->bytes.data() + end;', 'auto* dest = cur_->bytes.data() + prev.data + 2*prev.c;')
    # QA switch: use the stock eligibility limits on the same binary.
    once('if (count < 3 || count > 4096', '''static const bool original_limits=std::getenv("NGB_STRIP_JOIN_CONTROL")!=nullptr;
        if(original_limits && (prev.d!=1 || count>32 || prev.c>64))return false;
        if (count < 3 || count > 4096''')
    return t
