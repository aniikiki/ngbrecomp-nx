/* RecompXmm is a union, so ordinary function calls pass it through pairs of
 * integer registers. Keep packed operations as SSA vectors until publication. */
typedef float open_f4 __attribute__((vector_size(16)));
typedef unsigned open_u4 __attribute__((vector_size(16)));
typedef union {RecompXmm x;open_f4 f;open_u4 u;} open_vec;
#define OPEN_F(e) ((open_vec){.f=(e)}.x)
#define OPEN_U(e) ((open_vec){.u=(e)}.x)
#define OPEN_BITS(a) ((open_vec){.x=(a)}.u)
#define OPEN_FLOATS(a) ((open_vec){.x=(a)}.f)
#define XMM_ADD(a,b) OPEN_F(OPEN_FLOATS(a)+OPEN_FLOATS(b))
#define XMM_SUB(a,b) OPEN_F(OPEN_FLOATS(a)-OPEN_FLOATS(b))
#define XMM_MUL(a,b) OPEN_F(OPEN_FLOATS(a)*OPEN_FLOATS(b))
#define XMM_DIV(a,b) OPEN_F(OPEN_FLOATS(a)/OPEN_FLOATS(b))
#define XMM_XOR(a,b) OPEN_U(OPEN_BITS(a)^OPEN_BITS(b))
#define XMM_OR(a,b) OPEN_U(OPEN_BITS(a)|OPEN_BITS(b))
#define XMM_AND(a,b) OPEN_U(OPEN_BITS(a)&OPEN_BITS(b))
#define XMM_ANDN(a,b) OPEN_U(~OPEN_BITS(a)&OPEN_BITS(b))
#define XMM_SHUFFLE(a,b,imm) OPEN_U(__builtin_shufflevector(OPEN_BITS(a),OPEN_BITS(b), (imm)&3, ((imm)>>2)&3, 4+(((imm)>>4)&3),4+(((imm)>>6)&3)))
#define XMM_UNPACK_LOW(a,b) OPEN_U(__builtin_shufflevector(OPEN_BITS(a),OPEN_BITS(b),0,4,1,5))
#define XMM_UNPACK_HIGH(a,b) OPEN_U(__builtin_shufflevector(OPEN_BITS(a),OPEN_BITS(b),2,6,3,7))
