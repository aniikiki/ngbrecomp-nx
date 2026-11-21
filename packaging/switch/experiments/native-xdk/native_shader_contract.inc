// The game allocates vertex-program slots by reading the XDK object's size
// through its tagged handle. Exercise that protocol, not host-only metadata.
static void NativeShaderContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native shader contract failed", detail);
    };
    uint32_t scratch = NativePool(4096), stack = scratch + 1024;
    auto saved_state = g_state;
    auto saved_selected = g_selected;
    uint32_t saved_program[136][4];
    std::memcpy(saved_program, g_program, sizeof(g_program));
    const uint32_t declaration[] = {0x20000000, 0x40320000, 0xffffffff};
    std::memcpy(HostPtr(scratch, sizeof(declaration)), declaration, sizeof(declaration));
    std::vector<uint32_t> programs[2];
    uint32_t handles[2], slots[2], next = 135;
    for (unsigned i = 0; i < 2; ++i) {
        unsigned count = i ? 5 : 3;
        auto& words = programs[i]; words.resize(count * 4);
        // Distinct NOP streams, with an end marker only at each program's end.
        for (unsigned n = 0; n < count; ++n) words[n * 4] = 0x1000 + i * 256 + n;
        words.back() = 1;
        uint32_t function = scratch + 64 + i * 128, output = scratch + 512 + i * 4;
        W32(function, (count << 16) | 0x2078);
        std::memcpy(HostPtr(function + 4, words.size() * 4), words.data(), words.size() * 4);
        uint32_t regs[8]{}; regs[ESP] = stack;
        W32(stack + 4, scratch); W32(stack + 8, function);
        W32(stack + 12, output); W32(stack + 16, 0);
        NativeCall(D3DF_D3DDevice_CreateVertexShader, Call{regs});
        handles[i] = R32(output);
        require(!regs[EAX] && regs[ESP] == stack + 20 && (handles[i] & 1), 1 + i);
        // sub_001D4B10 reads handle + 7, which is object + 8, then subtracts
        // it from the next free slot. Zero made every shader overwrite slot 135.
        unsigned length = R32(handles[i] + 7);
        require(length == count, 0x10 + i);
        slots[i] = next -= length;
        regs[EAX] = handles[i]; regs[ESP] = stack; W32(stack + 4, slots[i]);
        NativeCall(D3DF_D3DDevice_LoadVertexShader, Call{regs});
        require(regs[ESP] == stack + 8, 0x20 + i);
        // Creation owns a copy; later source changes cannot alter the program.
        std::memset(HostPtr(function + 4, words.size() * 4), 0, words.size() * 4);
    }
    for (unsigned i : {0u, 1u, 0u}) {
        uint32_t regs[8]{}; regs[EAX] = handles[i]; regs[EBX] = slots[i]; regs[ESP] = stack;
        NativeCall(D3DF_D3DDevice_SelectVertexShader, Call{regs});
        require(regs[ESP] == stack + 4 && g_state.vs && g_state.vs->program == programs[i], 0x30 + i);
        require(g_state.vs->decl == g_vs.at(handles[i])->decl, 0x40 + i);
    }
    std::memcpy(g_program, saved_program, sizeof(g_program));
    g_selected = saved_selected; g_state = std::move(saved_state);
    std::fprintf(stderr, "[SHADER-CONTRACT-PASS] guest-sized slots preserve complete programs across selection\n");
}
