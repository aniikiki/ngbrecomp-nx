    /* A node belongs to the game's fixed pool of 768 five-word records.
     * Fold ordinary frame saves and node/key accesses into verified spans.
     * Resume the original epilogue after recursion, which can switch fibers. */
    if (esp >= NGB_VM_BEGIN + 24 && esp < NGB_RAM_BYTES - 16 && !(esp & 3)
        && !ngb_pending_dpcs && ngb_poll_mask - (ngb_guest_polls & ngb_poll_mask) >= 2) {
        unsigned offset = (esp - 24) & 4095;
        if (offset + 40 <= ngb_fast_page_bytes[(esp - 24) >> 12]) {
            uint32_t *frame = (uint32_t *)(ngb_fast_ram + esp);
            uint32_t node = frame[1], input = frame[2], mode = frame[3];
            if (node >= 0x950a78 && node <= 0x950a78 + 767*20 && !(node & 3) && mode < 5 &&
                (input & 4095) + 12 <= ngb_fast_page_bytes[input >> 12]) {
                uint32_t jump = MEM32(0x308cc4 + mode*4);
                if (jump == 0x00308c6d || jump == 0x00308c8e || jump == 0x00308cb9) {
                    uint32_t *record = (uint32_t *)(ngb_fast_ram + node);
                    uint32_t key;
                    frame[-1] = esi;
                    frame[-2] = edi;
                    esi = node;
                    memcpy(&key, ngb_fast_ram + (input & 0x7fffffffu) + 8, 4);
                    int left;
                    if (jump == 0x00308c8e) {
                        edi = key;
                        ecx = (int32_t)record[2] > (int32_t)key;
                        left = ecx;
                    } else {
                        float a, b;
                        memcpy(&a, &record[2], 4);
                        memcpy(&b, &key, 4);
                        xmm0 = XMM_SCALAR(jump == 0x00308c6d ? a : b);
                        left = jump == 0x00308c6d ? a > b : b > a;
                        ngb_guest_block_poll();
                    }
                    if (!left) ngb_guest_block_poll();
                    frame[-3] = mode;
                    frame[-4] = input;
                    eax = input;
                    edx = mode;
                    if (left) edx = record[3];
                    else eax = record[4];
                    frame[-5] = left ? edx : eax;
                    frame[-6] = left ? 0x00308cae : 0x00308c83;
                    esp -= 24;
                    RECOMP_ABI_CALL(0x00308BF0u, sub_00308BF0);
                    if (left) goto loc_00308CAE;
                    goto loc_00308C83;
                }
            }
        }
    }
