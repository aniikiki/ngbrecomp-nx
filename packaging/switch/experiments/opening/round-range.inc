static inline double ngb_round_range(double x){
 uint64_t bits; __builtin_memcpy(&bits,&x,8);
 unsigned e=(unsigned)(bits>>52)&2047u;
 if(__builtin_expect(e-897u<=252u,1))return (double)(float)x;
 return recomp_fp_round24(x);
}
#undef RECOMP_FP_PC
#define RECOMP_FP_PC(x) ((g_fp_control_word & 0x300u) ? (double)(x) : ngb_round_range(x))
