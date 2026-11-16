/* Normal binary64 inputs can be rounded to 24 significant bits directly.
 * Ties select the even significand. Retain the double exponent: casting
 * through float narrows the exponent and can introduce a second rounding.
 * The runtime uses the host default nearest-even mode. Preserve original
 * conversions for double subnormals, signed zero, NaNs and infinities. */
static inline double recomp_fp_round24(double x) {
    uint64_t b; __builtin_memcpy(&b,&x,8);
    unsigned exp=(unsigned)(b>>52)&2047u;
    if (__builtin_expect(exp && exp!=2047u,1)) {
        uint64_t rounded=(b+((UINT64_C(1)<<28)-1)+((b>>29)&1))&~((UINT64_C(1)<<29)-1);
        __builtin_memcpy(&x,&rounded,8);
        return x;
    }
    return recomp_fp_round24_reference(x);
}
