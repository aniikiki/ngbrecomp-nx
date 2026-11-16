"""Reuse private decoding storage, never retain guest pointers or live parser state."""
def transform(s):
 a=s.index('void RunPushBuffer(uint32_t pb) {')
 end=s.index('\n}',a);t=s[a:end]
 def sub(old,new,n=1):
  nonlocal t
  assert t.count(old)==n,old
  t=t.replace(old,new)
 sub('std::vector<uint16_t> idx;', '''static thread_local std::vector<uint16_t> spare;
    std::vector<uint16_t> idx;
    idx.swap(spare); // nested parsing gets a separate vector
    size_t used=0;
    bool allocated_this_call=false;''')
 sub('idx.clear();','used=0;')
 sub('uint32_t(idx.size()), reinterpret_cast<const uint8_t*>(idx.data())',
     'uint32_t(used), allocated_this_call ? reinterpret_cast<const uint8_t*>(idx.data()) : nullptr',2)
 sub('size_t first = idx.size();\n            idx.resize(first + size_t(count) * 2);',
     '''size_t first=used; used+=size_t(count)*2;
            if(used>idx.size()) idx.resize(used);
            allocated_this_call |= used!=0;''')
 sub('for (uint32_t i = 0; i < count; i++) idx.push_back(uint16_t(v[i]));',
     '''size_t first=used; used+=count;
            if(used>idx.size()) idx.resize(used);
            allocated_this_call |= used!=0;
            for(uint32_t i=0;i<count;i++) idx[first+i]=uint16_t(v[i]);''')
 sub('prim && !idx.empty()', 'prim && used')
 return s[:a]+t+'''
    if(idx.capacity()<=16384 && idx.capacity()>spare.capacity()) idx.swap(spare);
'''+s[end:]
