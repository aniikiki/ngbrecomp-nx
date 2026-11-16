"""Producer-only call counts and sampled CPU budget; no changes to snapshot decisions."""
def transform(s):
    def one(a,b):
        nonlocal s
        assert s.count(a)==1
        s=s.replace(a,b)
    one('struct IndexSnapshot {','''extern "C" unsigned long long snapshot_start(unsigned);
extern "C" void snapshot_end(unsigned,unsigned long long);
struct IndexSnapshot {''')
    k='        if (count < 64 || count > 4096) return {};'
    one(k,'''        struct Sample {
            unsigned long long start;
            ~Sample(){snapshot_end(0,start);}
        } sample{snapshot_start(0)};
'''+k)
    k='        copy->bounds = IndexRange(copy->bytes.data(), count);'
    one(k,'''        auto stamp=snapshot_start(1);
'''+k+'''
        snapshot_end(1,stamp);''')
    return s
