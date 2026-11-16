/* Count only calls on the guest thread in the selected window. Report reuse
 * without substituting results or changing FP exceptions / rounding. */
static _Thread_local unsigned angle_live;
static struct {
    uint64_t key[256], valid[4], calls, hits, reduced, reduced_hits;
} angle[3];
static inline void observe_angle(unsigned op, double x) {
    if (!angle_live) return;
    uint64_t bits;
    memcpy(&bits, &x, sizeof bits);
    uint64_t key = bits ^ (bits >> 32);
    unsigned idx = (unsigned)((key * UINT64_C(11400714819323198485)) >> 56);
    uint64_t mask = UINT64_C(1) << (idx%64);
    int hit = (angle[op].valid[idx/64]&mask) && angle[op].key[idx]==bits;
    angle[op].valid[idx/64] |= mask;
    angle[op].key[idx] = bits;
    angle[op].calls++;
    angle[op].hits += hit;
    if ((bits & UINT64_C(0x7fffffffffffffff)) > UINT64_C(0x3fe921fb54442d18)) {
        angle[op].reduced++;
        angle[op].reduced_hits+=hit;
    }
}
double __real_sin(double), __real_cos(double);
void __real_sincos(double,double*,double*);
double __wrap_sin(double x) {observe_angle(0,x);return __real_sin(x);}
double __wrap_cos(double x) {observe_angle(1,x);return __real_cos(x);}
void __wrap_sincos(double x,double*s,double*c) {observe_angle(2,x);__real_sincos(x,s,c);}
static void angle_frame(unsigned f) {
    if(f==30)angle_live=1;
    if(f==120){
        angle_live=0;
        for(unsigned i=0;i<3;i++)fprintf(stderr,"[ANGLE] op=%s calls=%llu hits=%llu large=%llu large_hits=%llu\n",
             (const char*[]){"sin","cos","sincos"}[i],(unsigned long long)angle[i].calls,
             (unsigned long long)angle[i].hits,(unsigned long long)angle[i].reduced,(unsigned long long)angle[i].reduced_hits);
    }
}
