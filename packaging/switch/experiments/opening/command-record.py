"""Shrink every recorded command. Only Copy and Present need Surface values;
keep those immutable snapshots with the owning batch until it is recycled."""
def transform(t):
    def once(a,b):
        nonlocal t
        assert t.count(a)==1,a
        t=t.replace(a,b)
    i=t.index('    int32_t vs = -1');j=t.index('\n};',i)
    assert t[i:j].count('Surface s1, s2;')==1
    t=t[:i]+t[j:]
    once('struct HeaderSend {','static_assert(sizeof(Cmd)==32);\nstruct HeaderSend {')
    once('    std::vector<Cmd> cmds;', '    std::vector<Surface> surfaces;\n    std::vector<Cmd> cmds;')
    once('        c.s1 = src;\n        c.s2 = dst;', '''        c.d=uint32_t(cur_->surfaces.size());
        cur_->surfaces.push_back(src);
        cur_->surfaces.push_back(dst);''')
    once('            c.s1 = front;', '''            c.d=uint32_t(cur_->surfaces.size());
            cur_->surfaces.push_back(front);''')
    once('c.quick = int32_t(cur_->quick.size());','c.b = uint32_t(cur_->quick.size());')
    once('b.quick[size_t(c.quick)]','b.quick[c.b]')
    once('Present(c.s1)','Present(b.surfaces[c.d])')
    once('Copy(c.s1, c.s2,','Copy(b.surfaces[c.d], b.surfaces[c.d+1],')
    once('        b->cmds.clear();','        b->surfaces.clear();\n        b->cmds.clear();')
    for arg,shader in [('a','vs'),('b','ps')]:
        once(f'c.{shader} = int32_t(cur_->{shader}.size());',f'c.{arg} = uint32_t(cur_->{shader}.size())+1;')
        once(f'if (c.{shader} >= 0) state_.{shader} = b.{shader}[size_t(c.{shader})];', f'if(c.{arg}) state_.{shader} = b.{shader}[c.{arg}-1];')
    once('c.vs < 0 && c.ps < 0','!c.a && !c.b')
    return t
