    /* Scan a single ordinary RAM page up to the next scheduled poll.
     * Codes 1 and 2 take one poll; every other value takes two. */
    if (edi >= 4 && !ngb_pending_dpcs) {
        unsigned slots = ngb_fast_page_bytes[esi >> 12];
        unsigned offset = esi & 4095;
        unsigned count = slots > offset ? (slots - offset) / 4 : 0;
        unsigned budget = (ngb_poll_mask - (ngb_guest_polls & ngb_poll_mask)) / 2;
        if (count > edi) count = edi;
        if (count > budget) count = budget;
        if (count >= 4) {
            const unsigned char *words = ngb_fast_ram + (esi & 0x7fffffffu);
            unsigned hits = 0, extra_polls = 0;
            for (unsigned i = 0; i < count; ++i) {
                uint32_t word;
                memcpy(&word, words + i*4, 4);
                uint32_t tag = word - 0x91000001u;
                hits += tag < 4;
                extra_polls += tag >= 2;
                edx = word;
            }
            SET_LO8(ebx, LO8(ebx) + hits);
            ngb_guest_polls += count + extra_polls;
            esi += count * 4;
            edi -= count;
            if (edi) goto loc_00149D40;
            goto loc_00149D6A;
        }
    }
