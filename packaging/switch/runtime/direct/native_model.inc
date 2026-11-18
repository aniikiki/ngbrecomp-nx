/* Model traversal for the ordinary and pass-filtered paths. These own the
 * world transform and submit all of the model's meshes in original order. */
void ngb_d3d_model_scope(int enter);
void ngb_d3d_model_world(uint32_t matrix);

static int model_body(int filtered)
{
    if (g_df) return 0;
    ngb_d3d_model_scope(1);
    RECOMP_ENTRY(filtered ? 0x00307A10u : 0x003078B0u);
    uint32_t bp = g_seh_ebp;
    edx = MEM32(esp + 8); esp -= 16;
    PUSH32(esp, ebx); PUSH32(esp, bp); PUSH32(esp, esi);
    esi = eax; eax = MEM32(0xd21e48); ebx = 0; bp = edx;
    int skip = 0;
    if ((int32_t)eax > 1) {
        ecx = MEM32(0xd21e40);
        if ((int32_t)eax > (int32_t)ecx) {
            eax -= ecx + 1; MEM32(esp + 12) = eax; skip = eax != 0;
        }
    }
    if (!skip) {
        PUSH32(esp, edi);
        if (MEM32(0x977bd4) != esi) {
            ngb_d3d_model_world(esi);
            esi += 64;
        }
        if (edx && MEM32(edx) == 0xffffffffu) {
            eax = MEM32(edx + 4);
            unsigned owner = ngb_d3d_model_suspend();
            PUSH32(esp, filtered ? 0x00307A82u : 0x00307922u); sub_0030C1A0();
            ngb_d3d_model_resume(owner);
            ecx = MEM32(esp + 0x28); eax = MEM32(ecx + 8);
            if (eax) {
                ebx = eax; eax = MEM32(ebx + 12);
                while (eax) {
                    mesh_poll(); ebx = eax; eax = MEM32(ebx + 12);
                }
            }
            if (filtered) mesh_poll();
            bp = MEM32(ecx + 16); edx = MEM32(esp + 0x28);
        }
        uint32_t model = MEM32(esp + 0x24);
        edi = model + 0x94; esi = 0;
        unsigned count = MEM32(model + 8);
        while (esi < count) {
            if (filtered || esi) mesh_poll();
            if (!filtered) mesh_poll();
            MEM32(esp + 0x14) = MEM32(esp + 0x18) = MEM32(esp + 0x1c) = 0;
            if (filtered && MEM8(edi - 3) != MEM8(esp + 0x2c)) {
                if (bp && MEM32(bp) == esi) bp = MEM32(bp + 16);
            } else {
                if (bp && MEM32(bp) == esi) {
                    MEM32(esp + 0x14) = MEM32(bp + 4);
                    if (ebx) {
                        MEM32(ebx + 12) = MEM32(bp + 8);
                        MEM32(esp + 0x18) = MEM32(edx + 8);
                    } else {
                        if (!filtered) mesh_poll();
                        MEM32(esp + 0x18) = MEM32(bp + 8);
                    }
                    MEM32(esp + 0x1c) = MEM32(bp + 12); bp = MEM32(bp + 16);
                } else {
                    if (!filtered) mesh_poll();
                    if (ebx) MEM32(esp + 0x18) = MEM32(edx + 8);
                }
                if (!filtered) mesh_poll();
                uint32_t opacity = MEM32(esp + (filtered ? 0x30 : 0x2c));
                uint32_t commands = esp + 0x14, material = MEM32(edi);
                PUSH32(esp, opacity); PUSH32(esp, commands); PUSH32(esp, material);
                PUSH32(esp, filtered ? 0x00307B42u : 0x003079CCu);
                if (!ngb_direct_mesh()) {
                    unsigned owner = ngb_d3d_model_suspend(); sub_0030BCA0(); ngb_d3d_model_resume(owner);
                }
                esp += 12; edx = MEM32(esp + 0x28);
            }
            model = MEM32(esp + 0x24); count = MEM32(model + 8);
            edi += 32; ++esi;
        }
        POP32(esp, edi);
        if (edx && MEM32(edx) == 0xffffffffu) {
            if (!filtered) mesh_poll();
            eax = MEM32(edx + 12);
            unsigned owner = ngb_d3d_model_suspend();
            PUSH32(esp, filtered ? 0x00307B6Eu : 0x003079FAu); sub_0030C1A0();
            ngb_d3d_model_resume(owner);
            if (ebx) MEM32(ebx + 12) = 0;
        }
    }
    if (!filtered) mesh_poll();
    POP32(esp, esi); POP32(esp, bp); POP32(esp, ebx); esp += 20;
    ngb_d3d_model_scope(0);
    return 1;
}

int ngb_direct_model(void) { return model_body(0); }
int ngb_direct_model_filtered(void) { return model_body(1); }
