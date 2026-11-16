"""Time HLE observation and the subsequent original XDK body separately.
Restrict to the actual SelectVertexShader call instruction in 1D6E20."""
def transform(h):
    call='    int took = d3d_hle_call(fn, regs);'
    ret='    if (!took) return 0;'
    after='void d3d_after(int fn)\n{'
    assert all(h.count(k)==1 for k in (call,ret,after))
    return ('extern unsigned tree_epoch;extern unsigned long long tree_begin(unsigned);'
            'extern void tree_end(unsigned,unsigned,unsigned long long);'
            'static unsigned body_epoch, body_active;static unsigned long long body_time;\n'+
            h.replace(call,'''    int watch=fn==D3DF_D3DDevice_SelectVertexShader && MEM32(esp)==0x001D700Fu;
    unsigned ep=tree_epoch; unsigned long long t=watch?tree_begin(0):0;
'''+call+'''
    if(t)tree_end(0,ep,t);''').replace(ret,'''    if (!took) {
        if(watch){if(body_active)abort();body_active=1;body_epoch=tree_epoch;body_time=tree_begin(1);}
        return 0;
    }''').replace(after,after+'''
    if(fn==D3DF_D3DDevice_SelectVertexShader && body_active){
        body_active=0;if(body_time)tree_end(1,body_epoch,body_time);
    }'''))
