"""Compare the actual x27 index with the live private ABI guest ESP page."""
def instrument(s):
    k='static unsigned page_rows[8192][2]'
    assert s.count(k)==1
    s=s.replace(k,'static unsigned page_rows[8192][3]')
    k='page_rows[pc_used][1]=(unsigned)page;'
    assert s.count(k)==1
    s=s.replace(k,k+'page_rows[pc_used][2]=(uint32_t)((ucontext_t*)ctx)->uc_mcontext.regs[22]>>12;')
    k='[PAGE_PC] %u %lx %x'
    assert s.count(k)==1
    return s.replace(k,'[STACK_DISTANCE] %u %lx %x %x').replace('page_rows[j][1]);','page_rows[j][1],page_rows[j][2]);').replace('991027:887123','331027:287123')
