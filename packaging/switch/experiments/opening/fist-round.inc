/* Explicit rounding directions, independent of host FPCR rounding mode. */
static inline int64_t ngb_arm_fist(double v, uint16_t control, unsigned bits) {
    double r;
    switch ((control>>10)&3u) {
    case 0: __asm__("frintn %d0,%d1":"=w"(r):"w"(v)); break;
    case 1: __asm__("frintm %d0,%d1":"=w"(r):"w"(v)); break;
    case 2: __asm__("frintp %d0,%d1":"=w"(r):"w"(v)); break;
    default: __asm__("frintz %d0,%d1":"=w"(r):"w"(v)); break;
    }
    double lim=ldexp(1.0,(int)bits-1);
    if (!(r >= -lim && r < lim))
        return bits==64?INT64_MIN:-(INT64_C(1)<<(bits-1));
    return (int64_t)r;
}
