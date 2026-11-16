"""Compute immutable index snapshot bounds once on the batch consumer."""
def transform(s):
    def one(a,b):
        nonlocal s
        assert s.count(a)==1,a
        s=s.replace(a,b)
    one('    IndexBounds bounds{};', '''    // Only ExecuteBatch accesses these fields after publication. Recording
    // can compare bytes concurrently; it never inspects or resets bounds.
    mutable IndexBounds bounds{};
    mutable bool have_bounds = false;
    const IndexBounds* Bounds() const {
        if (!have_bounds) {
            bounds = IndexRange(bytes.data(), static_cast<uint32_t>(bytes.size()/2));
            have_bounds = true;
        }
        return &bounds;
    }''')
    one('        copy->bounds = IndexRange(copy->bytes.data(), count);\n','')
    one('snapshot.bytes.data(), &snapshot.bounds','snapshot.bytes.data(), snapshot.Bounds()')
    return s
