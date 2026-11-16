"""Track armed slots and enumerate them in the same order, including reentrant updates."""
def transform(s):
 def one(a,b):
    nonlocal s
    assert s.count(a)==1,a
    s=s.replace(a,b)
 one('void ngb_timers_reset(void) {','unsigned ngb_armed_slots;\nvoid ngb_timers_reset(void) { ngb_armed_slots=0;')
 one('    memset(&timers[i]', '    ngb_armed_slots &= ~(1u<<i);\n    memset(&timers[i]')
 one('    timers[i].armed = 1;', '    timers[i].armed = 1; ngb_armed_slots |= 1u<<i;')
 one('    timers[i].armed = 0;\n    return previous;', '    timers[i].armed = 0; ngb_armed_slots &= ~(1u<<i);\n    return previous;')
 one('    for (int i = 0; i < 32; ++i) {','    unsigned left=~0u;\n    while (left & ngb_armed_slots) {\n        unsigned i=__builtin_ctz(left & ngb_armed_slots);\n        left &= ~((1u<<i) | ((1u<<i)-1u));')
 one('        else timers[i].armed = 0;', '        else {timers[i].armed = 0; ngb_armed_slots &= ~(1u<<i);}')
 return s
