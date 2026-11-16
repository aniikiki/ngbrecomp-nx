/* Only called by the recompiled guest's material function on its owner thread.
 * Leave exceptional inputs and non-default FPCR to libm. Keep signed zero keys
 * distinct; use exact libm output for misses, with no angle quantization. */
static unsigned cache_active = 1;
static double cached_material_angle(double x, unsigned cosine) {
    static struct entry {uint64_t key; double value; unsigned valid;} cache[2][256];
    uint64_t bits, fpcr;
    memcpy(&bits,&x,8);
    __asm__("mrs %0,fpcr":"=r"(fpcr));
    if(!cache_active || fpcr || (bits & UINT64_C(0x7ff0000000000000))==UINT64_C(0x7ff0000000000000))
        return cosine?cos(x):sin(x);
    unsigned i=(unsigned)(((bits^(bits>>32))*UINT64_C(11400714819323198485))>>56);
    struct entry *e=&cache[cosine][i];
    if(e->valid && e->key==bits) {
#ifdef NGB_ANGLE_VERIFY
        double ref=cosine?cos(x):sin(x);
        if(memcmp(&ref,&e->value,8)) abort();
#endif
        return e->value;
    }
    double value=cosine?cos(x):sin(x);
    e->key=bits;e->value=value;e->valid=1;
    return value;
}
double material_cos(double x){return cached_material_angle(x,1);}
double material_sin(double x){return cached_material_angle(x,0);}
