"""Copy the selected vertex instructions once; preserve a fresh object at every selection."""
def transform(s):
 def edit(old,new):
  nonlocal s
  assert s.count(old)==1,old
  s=s.replace(old,new)
 edit('uint32_t g_program[136][4];','uint32_t g_program[136 * 4];')
 edit('std::memcpy(g_program[at + i],','std::memcpy(g_program + (at + i)*4,')
 a=s.index('        for (uint32_t i = at; i < 136; i++) {')
 b=s.index('        vs->handle = h;',a)
 assert 'vs->program.insert' in s[a:b] and 'g_program[i][3] & 1' in s[a:b]
 s=s[:a]+'''        if (at < 136) {
            uint32_t end=at;
            do { ++end; } while (end < 136 && !(g_program[end*4-1] & 1));
            vs->program.assign(g_program + at*4, g_program + end*4);
        }
'''+s[b:]
 return s
