"""If a group is known different and all its earlier pieces were equal, its last piece differs."""
def transform(s):
    anchor='    void SendRange(const uint8_t* now, Range range) {'
    assert s.count(anchor)==1
    a=s.index(anchor);b=s.index('\n    }',a)
    body=s[a:b]
    def once(old,new):
        nonlocal body
        assert body.count(old)==1
        body=body.replace(old,new)
    once('Range range)', 'Range range, bool whole_diff = false)')
    once('if (group > kPiece && !std::memcmp', 'bool known=whole_diff && off==range.off && group==range.len;\n            if (!known && group > kPiece && !std::memcmp')
    once('size_t limit = off + group, first = off;', 'bool need_difference=known || group>kPiece;\n            size_t limit = off + group, first = off;')
    once('if (!std::memcmp(sent + off, now + off, n))', 'if (!(need_difference && off+n==limit) && !std::memcmp(sent + off, now + off, n))')
    once('first = off + n;\n                }','first = off + n;\n                } else need_difference=false;')
    s=s[:a]+body+s[b:]
    k='        else SendRange(now, r);'
    assert s.count(k)==1
    return s.replace(k,'        else SendRange(now, r, true);')
