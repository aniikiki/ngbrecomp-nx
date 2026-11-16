"""Time one of five disjoint sync regions, the full call, or empty control per draw."""
def transform(s):
    a=s.index('void SyncDeferred() {');b=s.index('\n}',a);v=s[a:b]
    keys=['std::memcpy(g_state.rs.data()', 'const auto* methods =', 'for (int s = 0;', '#ifdef NGB_DIRECT3D','uint32_t dev =']
    for j,k in enumerate(keys):
        assert v.count(k)==1
        pos=v.index(k);start=v.rfind('\n',0,pos)+1
        v=v[:start]+(f'    if (sb=={j-1}) sb_end(sb,t);\n' if j else '')+f'    if (sb=={j}) t=sb_now();\n'+v[start:]
    v=v.replace('void SyncDeferred() {','''extern "C" unsigned sb_pick();
extern "C" unsigned long long sb_now();
extern "C" void sb_end(unsigned,unsigned long long);
void SyncDeferred() {
    unsigned sb=sb_pick(); unsigned long long t=0;
    if(sb==5 || sb==6)t=sb_now();
    if(sb==6)sb_end(sb,t);''')
    return s[:a]+v+'\n    if(sb==4 || sb==5)sb_end(sb,t);'+s[b:]
