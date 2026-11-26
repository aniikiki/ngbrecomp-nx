/* The game's complete mesh submission, with the original callback order and
 * guest stack. The rendering adapter owns material/state preparation; only
 * game effects cross back into recompiled code. Included by hooks.c. */
extern uint32_t ngb_native_mesh_enabled;
int ngb_d3d_mesh_allowed(uint32_t material);
void ngb_d3d_mesh_scope(int enter);
int ngb_d3d_mesh_fixed(uint32_t material, uint32_t return_slot);
int ngb_d3d_mesh_texture(unsigned stage, uint32_t texture);
unsigned ngb_d3d_model_suspend(void);
void ngb_d3d_model_resume(unsigned depth);
void ngb_d3d_mesh_simple(uint32_t cache, unsigned state, unsigned method, uint32_t value);
void ngb_d3d_mesh_disable(unsigned stage);
void ngb_d3d_mesh_unbind(unsigned stage);
void ngb_d3d_mesh_modulate(unsigned stage, uint32_t color);
void ngb_d3d_mesh_draw(uint32_t material);

/* The runtime isolates native state around actual interrupts, guest callbacks
 * and full scheduler polls. A short poll with no callback preserves it. */
static void mesh_poll(void)
{
    ngb_guest_block_poll();
}

#define MESH_GAME_CALL(fn, ret) do { \
    unsigned mesh_owner = ngb_d3d_model_suspend(); PUSH32(esp, ret); fn(); \
    ngb_d3d_model_resume(mesh_owner); \
} while (0)
#define MESH_INDIRECT(target, before, ret, site) do { \
    uint32_t mesh_target = (target); \
    unsigned mesh_owner = ngb_d3d_model_suspend(); PUSH32(esp, ret); \
    RECOMP_ICALL_SAFE_AT(mesh_target, before, site); \
    ngb_d3d_model_resume(mesh_owner); \
} while (0)

static int mesh_next_entry_can_yield(void)
{
    return ngb_pending_dpcs || !((ngb_guest_polls + 1) & ngb_poll_mask);
}

// The particle callback reads three overrides. With all three disabled it
// only touches guest registers and its two stack spills. Let the real callback
// execute, retaining the renderer state already prepared for the next draw.
static int mesh_particle_uses_defaults(uint32_t particle)
{
    if (mesh_next_entry_can_yield()) return 0;
    if (!particle) return 1;
    const uint8_t *flags = (const uint8_t *)ngb_ram_span(particle + 0x222, 10);
    const void *spill = ngb_ram_span(esp - 8, 8);
    if (!flags || !spill) return 0;
    uintptr_t f = (uintptr_t)flags, s = (uintptr_t)spill;
    if (s < f + 10 && f < s + 8) return 0;
    uint16_t blend_mode, blend_op;
    memcpy(&blend_mode, flags, sizeof blend_mode);
    memcpy(&blend_op, flags + 2, sizeof blend_op);
    return blend_mode == 6 && blend_op == 2 && !flags[9];
}

static void mesh_global_command(void)
{
    PUSH32(esp, 0x0030C27Du);
    // The guest jump table is live. If another worker can run at the
    // decoder's entry, let the decoder read the opcode after that checkpoint.
    const uint8_t *opcode = (const uint8_t *)ngb_ram_span(eax + 1, 1);
    if (mesh_next_entry_can_yield() || !opcode || *opcode != 10 || MEM32(0x30c360) != 0x0030C32Eu) {
        unsigned owner = ngb_d3d_model_suspend();
        sub_0030C2A0();
        ngb_d3d_model_resume(owner);
        return;
    }
    RECOMP_ENTRY(0x0030C2A0u);
    ecx = MEM32(eax + 8);
    uint32_t before = esp;
    PUSH32(esp, ecx);
    uint32_t callback = MEM32(eax + 4);
    PUSH32(esp, 0x0030C335u);
    // 001D7800 only stores its argument in the model's lighting context.
    int preserves_state = callback == 0x001D7800u ||
        (callback == 0x00127290u && mesh_particle_uses_defaults(MEM32(esp + 4)));
    unsigned owner = preserves_state ? 0 : ngb_d3d_model_suspend();
    RECOMP_ICALL_SAFE_AT(callback, before, 0x0030C332u);
    if (!preserves_state) ngb_d3d_model_resume(owner);
    POP32(esp, ecx);
    esp += 4;
}

static void mesh_command_call(uint32_t ret)
{
    PUSH32(esp, ret);
    RECOMP_ENTRY(0x0030C240u);
    // Even an empty list reaches the guest scheduler. After that checkpoint
    // its only visible work is spilling ESI below the return address.
    if (!eax) {
        void *spill = ngb_ram_span(esp - 4, sizeof(uint32_t));
        if (spill) {
            uint32_t saved = esi;
            memcpy(spill, &saved, sizeof saved);
            esp += 4;
            return;
        }
    }
    PUSH32(esp, esi);
    esi = eax;
    while (esi) {
        mesh_poll();
        SET_LO8(eax, MEM8(esi));
        if (LO8(eax) == 0xfe) {
            eax = (uint32_t)(int32_t)SMEM8(esi + 1) - 10;
            if (!eax) {
                ecx = MEM32(esi + 8);
                uint32_t before = esp;
                PUSH32(esp, ecx);
                MESH_INDIRECT(MEM32(esi + 4), before, 0x0030C26Du, 0x0030C26Au);
                esp += 4;
            } else if (!--eax) {
                eax = MEM32(esi + 8);
                uint32_t before = esp;
                PUSH32(esp, edi); PUSH32(esp, eax);
                MESH_INDIRECT(MEM32(esi + 4), before, 0x0030C261u, 0x0030C25Eu);
                esp += 8;
            }
        } else {
            mesh_poll();
            if (LO8(eax) == 0xff) {
                eax = esi;
                mesh_global_command();
            } else {
                eax = (uint32_t)(int32_t)(int8_t)LO8(eax); ecx = esi;
                MESH_GAME_CALL(sub_0030C370, 0x0030C289u);
            }
        }
        esi = MEM32(esi + 12);
    }
    POP32(esp, esi);
    esp += 4;
}

static void mesh_body(void)
{
    ngb_direct_mesh_scope(1);
    ngb_d3d_mesh_scope(1);
    RECOMP_ENTRY(0x0030BCA0u);
    uint32_t bp = g_seh_ebp;
    esp -= 8;
    xmm1 = XMM_ZERO();
    xmm0 = XMM_SCALAR(MEMF(esp + 0x14));
    PUSH32(esp, ebx); PUSH32(esp, bp);
    bp = ebx = 0;
    MEM32(esp + 8) = 0;
    if (!(0.0f >= xmm0.f[0])) {
        eax = MEM32(MEM32(esp + 0x18));
        PUSH32(esp, esi); esi = MEM32(esp + 0x18);
        PUSH32(esp, edi); edi = esi;
        MEMF(0x44b3c4) = xmm0.f[0];
        mesh_command_call(0x0030BCDAu);
        if (MEM32(0xc05fcc)) {
            mesh_poll();
            xmm0 = XMM_SCALAR(MEMF(0x44b438));
            MEMF(esp + 0x24) = xmm0.f[0]; MEM32(0xc05fcc) = 0;
        } else xmm0 = XMM_SCALAR(MEMF(esp + 0x24));
        xmm1 = XMM_SCALAR(MEMF(0x4148c8));
        if (xmm1.f[0] > xmm0.f[0]) {
            if (MEM32(esi + 0x38) != 0x302) MEM32(esp + 0x10) = 1;
            else {
                ebx = MEM32(esi + 0x20) ? esi + 0x60 : 0;
                if (ebx) {
                    xmm1 = XMM_SCALAR(MEMF(ebx + 12));
                    MEMF(esp + 0x14) = xmm1.f[0];
                    xmm1.f[0] *= xmm0.f[0]; MEMF(ebx + 12) = xmm1.f[0];
                    MEM32(esp + 0x10) = 2;
                } else MEM32(esp + 0x10) = 3;
            }
        }
        PUSH32(esp, 0x0030BD57u);
        int stage_ready = ngb_d3d_mesh_fixed(esi, esp);
        esp += 4;
        ecx = MEM32(esp + 0x1c);
        if (stage_ready && ecx == esi && !ngb_pending_dpcs && ((ngb_guest_polls + 1) & ngb_poll_mask)) {
            // One texture-stage poll, with no scheduled callback. Preserve
            // the texture call's stack spill and the loop's exit registers.
            ++ngb_guest_polls;
            MEM32(esp - 4) = 0x0030BD7Eu;
            eax = bp = 1; edi = ecx + 0xa0;
        } else {
            eax = MEM32(ecx + 8);
            edi = eax ? ecx + 0x60 + (MEM32(ecx + 0x20) ? 0x50 : 0) : 0;
            while (bp < eax) {
                mesh_poll(); eax = bp;
                PUSH32(esp, 0x0030BD7Eu);
                if (ngb_d3d_mesh_texture(eax, edi)) esp += 4;
                else {
                    unsigned owner = ngb_d3d_model_suspend(); sub_0030BA30(); ngb_d3d_model_resume(owner);
                }
                ecx = MEM32(esp + 0x1c); eax = MEM32(ecx + 8);
                ++bp; edi += 0x40;
            }
        }
        esi = MEM32(esp + 0x10); edi = 1;
        if (esi == 1) {
            g_fp_top = (g_fp_top + 7u) & 7u;
            g_fp_stack[g_fp_top] = RECOMP_FP_PC((double)MEMF(esp + 0x24) * MEMF(0x414920));
            PUSH32(esp, 0x0030BDA9u); sub_0036FDB8();
            edi = eax; eax = MEM32(0x9777fc);
            edx = ((edi | 0xffffff00u) << 8 | edi) << 8;
            edi |= edx;
            ngb_d3d_mesh_simple(0x9777fc, 75, 0x34c, edi);
            eax = MEM32(esp + 0x1c);
            if (MEM32(eax + 0x38) == 1) {
                eax = MEM32(0x9777c8); edi = 0x8001;
                ngb_d3d_mesh_simple(0x9777c8, 62, 0x344, edi);
            }
        } else if (esi == 2) {
            xmm0 = XMM_SCALAR(MEMF(esp + 0x14)); MEMF(ebx + 12) = xmm0.f[0];
            ngb_d3d_mesh_simple(0x9777bc, 59, 0x304, edi);
        }
        edi = MEM32(esp + 0x1c) + 0x50;
        SET_LO8(eax, MEM8(edi));
        if (LO8(eax)) {
            mesh_poll();
            do {
                mesh_poll(); ecx = LO8(eax); eax = MEM32(0x44b410 + ecx * 4);
                if (eax) {
                    edx = MEM32(esp + 0x1c);
                    uint32_t before = esp; PUSH32(esp, edx);
                    MESH_INDIRECT(eax, before, 0x0030BE65u, 0x0030BE63u);
                    esp += 4;
                }
                SET_LO8(eax, MEM8(++edi));
            } while (LO8(eax));
        }
        edi = 3; ebx = 4;
        if (esi == 3) {
            g_fp_top = (g_fp_top + 7u) & 7u;
            g_fp_stack[g_fp_top] = RECOMP_FP_PC((double)MEMF(esp + 0x24) * MEMF(0x414920));
            PUSH32(esp, 0x0030BE91u); sub_0036FDB8();
            esi = 1;
            ngb_d3d_mesh_modulate(bp, (eax << 24) | 0xffffff);
            ++bp;
            ngb_d3d_mesh_simple(0x9777bc, 59, 0x304, 1);
        } else esi = 1;
        if (bp < 4) {
            edi = MEM32(0xc0ebb0);
            ngb_d3d_mesh_disable(bp);
            ngb_d3d_mesh_unbind(bp);
            MEM32(0xc0ebb0) = bp;
            while (bp < edi) {
                mesh_poll(); ++bp;
                ngb_d3d_mesh_unbind(bp);
            }
        }
        ebx = MEM32(esp + 0x20); edi = MEM32(esp + 0x1c);
        eax = MEM32(ebx + 4); mesh_command_call(0x0030C064u);
        bp = edi;
        ngb_d3d_mesh_draw(bp);
        eax = MEM32(ebx + 8); edi = bp; mesh_command_call(0x0030C0BCu);
        edi = bp + 0x50; SET_LO8(eax, MEM8(edi));
        while (LO8(eax)) {
            mesh_poll(); edx = LO8(eax); eax = MEM32(0x44b424 + edx * 4);
            if (eax) {
                uint32_t before = esp; PUSH32(esp, bp);
                MESH_INDIRECT(eax, before, 0x0030C0E1u, 0x0030C0DFu);
                esp += 4;
            }
            SET_LO8(eax, MEM8(++edi));
        }
        xmm0 = XMM_SCALAR(MEMF(0x41494c));
        POP32(esp, edi); MEMF(0x44b3c4) = xmm0.f[0]; POP32(esp, esi);
    }
    POP32(esp, bp); POP32(esp, ebx); esp += 12;
    ngb_d3d_mesh_scope(0);
    ngb_direct_mesh_scope(0);
}

int ngb_direct_mesh(void)
{
    if (g_df) return 0;
    // The original early-out never dereferences a hidden mesh's material.
    if (!(0.0f >= MEMF(esp + 12)) && !ngb_d3d_mesh_allowed(MEM32(esp + 4))) return 0;
    mesh_body();
    return 1;
}

#undef MESH_GAME_CALL
#undef MESH_INDIRECT
