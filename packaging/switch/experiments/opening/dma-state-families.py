"""Accept additional complete incrementing Kelvin state packets in the existing guarded retire path."""
def transform(s):
 k='    unsigned run = method == NV097_SET_TRANSFORM_CONSTANT_LOAD ? 1 : direct_state_words(method);'
 assert s.count(k)==1
 return s.replace(k,'''    /* Direct3D already consumed these registers. Only accept the observed
       starts and cap the complete span; do not change partial-packet dispatch. */
    unsigned run;
    switch (method) {
    case 0x194c: case 0x1950: case 0x195c: case 0x1960:
    case NV097_SET_SHADOW_DEPTH_FUNC: run=1; break;
    case NV097_SET_CLIP_MIN: run=2; break;
    case NV097_SET_VIEWPORT_OFFSET: case NV097_SET_VIEWPORT_SCALE: run=4; break;
    case NV097_SET_COMBINER_ALPHA_ICW: run=8; break;
    case NV097_SET_COMBINER_FACTOR0: run=32; break;
    default: run=method == NV097_SET_TRANSFORM_CONSTANT_LOAD ? 1 : direct_state_words(method);
    }''')
