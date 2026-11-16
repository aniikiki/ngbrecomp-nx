/* Private ABI only. The entry stub already initializes x28 with &g_regs.
 * Ordinary services continue to see the original exported data symbols. */
register RecompRegs *ngb_statep asm("x28");
#undef RECOMP_REGS
#define RECOMP_REGS (*ngb_statep)
typedef struct {
    RecompRegs regs;
    unsigned char pad[512-sizeof(RecompRegs)];
    uint64_t entries,polls;
    uint32_t mask,pending,va;
    uint32_t recent[32];
} NgPrivateState;
_Static_assert(__builtin_offsetof(NgPrivateState,recent)==540,"ARM state layout");
#define NG_STATE ((NgPrivateState *)(void *)ngb_statep)
