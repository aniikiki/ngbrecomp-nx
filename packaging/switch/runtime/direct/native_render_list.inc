void ngb_d3d_prepared_line(uint32_t regs[8]);

/* The original line routine writes these title registers only on a mismatch.
 * Admit the read-only setup only while its entry, blend helper and two loop
 * polls cannot dispatch another guest worker. The normal path handles changes. */
static int line_state_ready(uint32_t input)
{
    if (ngb_pending_dpcs || ngb_poll_mask - (ngb_guest_polls & ngb_poll_mask) < 4 ||
        (MEM16(input + 12) == 1 && !MEM16(input + 14))) return 0;

    // FVF, fill, the three identity transforms, depth, bindings, light and fog.
    if (MEM32(0x9776c8) != 0x42 || MEM32(0x9778fc) != 0x1b02 ||
        MEM32(0x977bd4) != 0x950140 || MEM32(0x977bd8) != 0x950140 ||
        MEM32(0x977bdc) != 0x950140 || MEM32(0x9777d0) != 0 ||
        MEM32(0x97790c) != (MEM32(input + 8) != 0) ||
        MEM32(0x977968) || MEM32(0x97796c) || MEM32(0x977868) || MEM32(0x977840)) return 0;
    // Select vertex colour/alpha on stage zero and disable stage one.
    if (MEM32(0x9779a8) != 2 || MEM32(0x9779b0) != 0 || MEM32(0x9779b8) != 2 ||
        MEM32(0x9779c0) != 0 || MEM32(0x977a28) != 1 || MEM32(0x977a38) != 1) return 0;

    uint32_t blend = 0x44b788 + 12u * MEM16(input + 18);
    return MEM32(blend) == MEM32(0x9777bc) && MEM32(blend + 4) == MEM32(0x9777c8) &&
           MEM32(blend + 8) == MEM32(0x9777cc);
}

static void line_draw(uint32_t primitive, uint32_t count, uint32_t vertices, uint32_t ret)
{
    PUSH32(esp, 16);
    PUSH32(esp, vertices);
    PUSH32(esp, count);
    PUSH32(esp, primitive);
    PUSH32(esp, ret);
    uint32_t regs[] = {eax, ecx, edx, ebx, esp, g_ebp, esi, edi};
    ngb_d3d_prepared_line(regs);
    esp = regs[4];
}

static void line_width(uint32_t ret)
{
    if (eax == ecx) return;
    PUSH32(esp, eax);
    MEM32(0x977944) = eax;
    PUSH32(esp, ret);
    d3d_hook(D3DF_D3DDevice_SetRenderState_LineWidth);
}

// The guest's unsigned 16-bit counts fit in a signed 32-bit quotient. It
// rereads both counts after drawing each strip, including after a guest poll.
static void line_strip_count(void)
{
    uint32_t total = MEM16(ebx + 16);
    if (!ecx) ngb_stop("zero vertices per line strip", ebx);
    eax = total / ecx;
    edx = total % ecx;
}

static void render_prepared_line(void)
{
    RECOMP_ENTRY(0x00318410u);
    ecx = MEM32(0x977bd4);
    PUSH32(esp, ebx);
    PUSH32(esp, g_seh_ebp);
    PUSH32(esp, esi);
    PUSH32(esp, edi);
    edx = 0x200;
    ebx = MEM32(esp + 20);
    eax = MEM16(ebx + 18);
    PUSH32(esp, 0x003184B9u);
    sub_0030D6D0();
    edi = 0;
    eax = MEM32(ebx + 8);
    if (!eax) mesh_poll();
    esi = 1;
    eax = 0x800;
    mesh_poll();
    xmm0 = XMM_SCALAR(MEMF(ebx + 4));
    ecx = MEM32(0x977944);
    MEMF(esp + 20) = xmm0.f[0];
    eax = MEM32(esp + 20);
    line_width(0x0031874Cu);
    eax = (uint32_t)(int32_t)(int16_t)MEM16(ebx + 12) - edi;
    if (!eax) {
        edx = 2u * MEM16(ebx + 14);
        ecx = MEM32(ebx);
        line_draw(2, edx, ecx, 0x003187A6u);
    } else if (!--eax) {
        ecx = MEM16(ebx + 14);
        line_strip_count();
        edi = MEM32(ebx);
        esi = 0;
        while ((int32_t)esi < (int32_t)eax) {
            mesh_poll();
            line_draw(4, ecx, edi, 0x0031877Bu);
            ecx = MEM16(ebx + 14);
            edi += ecx * 16;
            line_strip_count();
            ++esi;
        }
    }
    xmm0 = XMM_SCALAR(MEMF(0x4148c8));
    ecx = MEM32(0x977944);
    POP32(esp, edi);
    MEMF(esp + 16) = xmm0.f[0];
    eax = MEM32(esp + 16);
    POP32(esp, esi);
    uint32_t saved_bp;
    POP32(esp, saved_bp);
    (void)saved_bp;
    POP32(esp, ebx);
    line_width(0x003187D1u);
    esp += 4;
}

static void submit_list_model(void)
{
    if (!model_body(0, 1)) {
        unsigned owner = ngb_d3d_model_suspend();
        sub_003078B0();
        ngb_d3d_model_resume(owner);
    }
    esp += 12;
}

static void render_model(void)
{
    RECOMP_ENTRY(0x001CB260u);
    eax = MEM32(esp + 4);
    ecx = MEM32(eax + 16);
    edx = MEM32(eax + 20);
    PUSH32(esp, ecx);
    ecx = MEM32(eax + 8);
    eax = MEM32(eax);
    PUSH32(esp, edx);
    PUSH32(esp, ecx);
    PUSH32(esp, 0x001CB277u);
    submit_list_model();
    esp += 4;
}

static void render_lit_model(void)
{
    RECOMP_ENTRY(0x001CB510u);
    PUSH32(esp, esi);
    esi = MEM32(esp + 8);
    // These two guest routines may edit device state and resource headers.
    // Only the model submission that follows can carry state to the next item.
    unsigned owner = ngb_d3d_model_suspend();
    eax = esi + 0x2c;
    PUSH32(esp, eax);
    PUSH32(esp, 0x001CB51Eu);
    sub_00308130();
    esp += 4;
    eax = MEM32(esi + 0x3c);
    if (eax) {
        PUSH32(esp, 0x001CB52Du);
        sub_0030B020();
    }
    ngb_d3d_model_resume(owner);
    ecx = MEM32(esi + 0x24);
    edx = MEM32(esi + 0x18);
    eax = MEM32(esi + 0x14);
    PUSH32(esp, ecx);
    PUSH32(esp, edx);
    PUSH32(esp, eax);
    eax = MEM32(esi + 0x1c);
    PUSH32(esp, 0x001CB541u);
    submit_list_model();
    POP32(esp, esi);
    esp += 4;
}

/* The ordered render tree is live guest memory. A callback can relink the
 * list, so visit children first and read the next link only after dispatch. */
static void render_list_walk(int *owns_state)
{
    RECOMP_ENTRY(0x00308D50u);
    PUSH32(esp, esi);
    esi = MEM32(esp + 8);
    while (esi) {
        mesh_poll();
        eax = MEM32(esi + 12);
        PUSH32(esp, eax);
        PUSH32(esp, 0x00308D69u);
        render_list_walk(owns_state);

        ecx = MEM32(esi);
        uint32_t before = esp;
        PUSH32(esp, ecx);
        uint32_t target = MEM32(esi + 4);
        PUSH32(esp, 0x00308D6Fu);
        int model = target == 0x001CB260u || target == 0x001CB510u;
        int line = target == 0x00318410u;
        if ((model || line) && !g_df && RECOMP_ICALL_IS_CODE(target) &&
            (model || line_state_ready(ecx))) {
            g_icall_trace[g_icall_trace_idx & (ICALL_TRACE_SIZE - 1)] = target;
            ++g_icall_trace_idx;
            ++g_icall_count;
            RECOMP_ICALL_OBSERVE_SITE(0x00308D6Cu, target);
            RECOMP_ICALL_OBSERVE(target, RECOMP_ICALL_SEEN_RESOLVED);
            if (!*owns_state) {
                ngb_d3d_model_scope(1);
                *owns_state = 1;
            }
            if (target == 0x001CB510u) render_lit_model();
            else if (model) render_model();
            else render_prepared_line();
        } else {
            if (*owns_state) {
                ngb_d3d_model_scope(0);
                *owns_state = 0;
            }
            RECOMP_ICALL_SAFE_AT(target, before, 0x00308D6Cu);
        }
        esi = MEM32(esi + 16);
        esp += 8;
    }
    POP32(esp, esi);
    esp += 4;
}

int ngb_direct_render_list(void)
{
    if (g_df || !ngb_native_mesh_enabled || !ngb_d3d_native_enabled()) return 0;
    unsigned parent = ngb_d3d_model_suspend();
    int owns_state = 0;
    render_list_walk(&owns_state);
    if (owns_state) ngb_d3d_model_scope(0);
    ngb_d3d_model_resume(parent);
    return 1;
}
