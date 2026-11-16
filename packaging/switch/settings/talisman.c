/* Switch port of the v0.9.70 death check. */
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"

/* Talisman of Rebirth (Gameplay, setting 43): sub_002FD3E0 is asked, as Ryu's health reaches 0, whether he
 * dies (al 1); with a Talisman of Rebirth (item 0xFB, counted by sub_001542C0) it brings him back
 * (sub_002FD470) and takes one away (al 0). Off: never used, Ryu dies with them kept. */
int ngb_pc_setting(int which);

/**
 * sub_002FD3E0
 * Original: 0x002FD3E0 - 0x002FD46A (138 bytes, 55 insns)
 * CC: cdecl, 0 params, returns int_or_void
 * Frame: fpo_leaf
 */
void sub_002FD3E0(void)
{
    RECOMP_ENTRY(0x002FD3E0u);
    int _flags = 0; /* fallback flag var */
    uint32_t _fa = 0, _fb = 0;
    int32_t _fas = 0, _fbs = 0;
    (void)_fa; (void)_fb; (void)_fas; (void)_fbs;

loc_002FD3E0: ;
    PUSH32(esp, ebx);
    PUSH32(esp, esi);
    esi = eax;
    ecx = esi;
    _fb = (uint32_t)(0x4B4E50) & 0xFFFFFFFFu; _fbs = (int32_t)(int32_t)(_fb); /* sub source, before the write */
    ecx = ecx - 0x4B4E50;
    _fa = (uint32_t)(ecx) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* sub result */
    eax = 0x66666667;
    { int64_t _r = (int64_t)(int32_t)eax * (int64_t)(int32_t)ecx;
      eax = (uint32_t)_r; edx = (uint32_t)(_r >> 32); _fa = eax; _fas = (int32_t)eax; _fb = (_r != (int64_t)(int32_t)_r); }
    edx = (uint32_t)(((int32_t)(int32_t)(edx)) >> ((0xC) & 31u));
    _fa = (uint32_t)(edx) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* sar result */
    eax = edx;
    eax = eax >> 0x1F;
    _fa = (uint32_t)(eax) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* shift result */
    _fb = (uint32_t)(edx) & 0xFFFFFFFFu; _fbs = (int32_t)(int32_t)(_fb); /* add source, before the write */
    eax = eax + edx;
    _fa = (uint32_t)(eax) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* add result */
    SET_LO8(ebx, 1);
    if ((_fas < 0)) goto loc_002FD465; /* js: sign (negative) */

loc_002FD401: ;
    _fa = (uint32_t)(eax) & 0xFFFFFFFFu; _fb = (uint32_t)(0x40) & 0xFFFFFFFFu;
    _fas = (int32_t)(int32_t)(_fa); _fbs = (int32_t)(int32_t)(_fb); /* cmp eax, 0x40 (32-bit) */
    if (CMP_GE(_fas, _fbs)) goto loc_002FD465; /* jge: greater or equal (signed >=) */

loc_002FD406: ;
    PUSH32(esp, edi);
    edi = ZX8(MEM8(esi + 0x27F0));
    { int64_t _r = (int64_t)(int32_t)(edi) * (int64_t)(int32_t)(0x210);
      edi = (uint32_t)_r;
      _fa = (uint32_t)_r & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); _fb = (_r != (int64_t)(int32_t)_r); } /* imul */
    _fb = (uint32_t)(0x58A3A0) & 0xFFFFFFFFu; _fbs = (int32_t)(int32_t)(_fb); /* add source, before the write */
    edi = edi + 0x58A3A0;
    _fa = (uint32_t)(edi) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* add result */
    SET_LO8(ecx, MEM8(edi + 0x1F4));
    _fa = (uint32_t)(LO8(ecx)) & 0xFFu; _fb = (uint32_t)(0) & 0xFFu;
    _fas = (int32_t)(int8_t)(_fa); _fbs = (int32_t)(int8_t)(_fb); /* cmp LO8(ecx), 0 (8-bit) */
    if (CMP_NE(_fa, _fb)) goto loc_002FD42A; /* jne: not equal / not zero */

loc_002FD424: ;
    POP32(esp, edi);
    POP32(esp, esi);
    SET_LO8(eax, 1);
    POP32(esp, ebx);
    esp += 4; return; /* ret */

loc_002FD42A: ;
    _fa = (uint32_t)(MEM16(edi + 0x1C6)) & 0xFFFFu; _fb = (uint32_t)(0) & 0xFFFFu;
    _fas = (int32_t)(int16_t)(_fa); _fbs = (int32_t)(int16_t)(_fb); /* cmp MEM16(edi + 0x1C6), 0 (16-bit) */
    if (CMP_BE(_fa, _fb)) goto loc_002FD43A; /* jbe: below or equal (unsigned <=) */

loc_002FD434: ;
    POP32(esp, edi);
    POP32(esp, esi);
    SET_LO8(eax, 0); /* xor self */
    _fa = (uint32_t)(LO8(eax)) & 0xFFu; _fas = (int32_t)(int8_t)(_fa); /* xor result */
    POP32(esp, ebx);
    esp += 4; return; /* ret */

loc_002FD43A: ;
    _fa = (uint32_t)(eax) & 0xFFFFFFFFu; _fb = (uint32_t)(0) & 0xFFFFFFFFu;
    _fas = (int32_t)(int32_t)(_fa); _fbs = (int32_t)(int32_t)(_fb); /* cmp eax, 0 (32-bit) */
    if (CMP_NE(_fa, _fb)) goto loc_002FD424; /* jne: not equal / not zero */

loc_002FD43E: ;
    esi = 0xFB;
    if (!ngb_pc_setting(43))                     /* Talisman of Rebirth Off: as if none were had -- Ryu dies */
        goto loc_002FD45F;                       /* (bl still 1: dead) */
    PUSH32(esp, 0x002FD448u); RECOMP_ABI_CALL(0x001542C0u, sub_001542C0); /* call 0x001542C0 */

loc_002FD448: ;
    _fa = (uint32_t)(eax) & 0xFFFFFFFFu; _fb = (uint32_t)(0) & 0xFFFFFFFFu;
    _fas = (int32_t)(int32_t)(_fa); _fbs = (int32_t)(int32_t)(_fb); /* cmp eax, 0 (32-bit) */
    if (CMP_EQ(_fa, _fb)) goto loc_002FD45F; /* je: equal / zero */

loc_002FD44C: ;
    ecx = edi;
    PUSH32(esp, 0x002FD453u); RECOMP_ABI_CALL(0x002FD470u, sub_002FD470); /* call 0x002FD470 */

loc_002FD453: ;
    ebx = ebx | 0xFFFFFFFFu;
    _fa = (uint32_t)(ebx) & 0xFFFFFFFFu; _fas = (int32_t)(int32_t)(_fa); /* or result */
    eax = esi;
    { uint32_t _icall_esp = g_esp;
    PUSH32(esp, 0x002FD45Du); RECOMP_ICALL_SAFE(0x00154300u, _icall_esp); /* manual call 0x00154300 */
    }

loc_002FD45D: ;
    SET_LO8(ebx, 0); /* xor self */
    _fa = (uint32_t)(LO8(ebx)) & 0xFFu; _fas = (int32_t)(int8_t)(_fa); /* xor result */

loc_002FD45F: ;
    POP32(esp, edi);
    POP32(esp, esi);
    SET_LO8(eax, LO8(ebx));
    POP32(esp, ebx);
    esp += 4; return; /* ret */

loc_002FD465: ;
    POP32(esp, esi);
    SET_LO8(eax, 1);
    POP32(esp, ebx);
    esp += 4; return; /* ret */

}
