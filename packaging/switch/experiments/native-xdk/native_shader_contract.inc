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
    auto select = [&](uint32_t handle, uint32_t at) {
        uint32_t regs[8]{}; regs[EAX] = handle; regs[EBX] = at; regs[ESP] = stack;
        NativeCall(D3DF_D3DDevice_SelectVertexShader, Call{regs});
        require(regs[ESP] == stack + 4 && g_state.vs && g_state.vs_handle == (handle | 1), 0x30);
        return g_state.vs;
    };
    auto load = [&](uint32_t handle, uint32_t at) {
        uint32_t regs[8]{}; regs[EAX] = handle; regs[ESP] = stack; W32(stack + 4, at);
        NativeCall(D3DF_D3DDevice_LoadVertexShader, Call{regs});
    };
    for (unsigned i : {0u, 1u}) {
        auto shader = select(handles[i], slots[i]);
        require(shader->program == programs[i] && shader->decl == g_vs.at(handles[i])->decl, 0x40 + i);
    }
    auto original = select(handles[0], slots[0]);
    load(handles[0], slots[0]);
    load(handles[1], 0);
    require(select(handles[0], slots[0]) == original, 0x42);
    // Overwrite the previous end and extend it by one instruction to the bank boundary.
    load(handles[1], slots[0] + 1);
    auto extended = select(handles[0], slots[0]);
    auto expected = programs[0]; expected.resize(4);
    expected.insert(expected.end(), programs[1].begin(), programs[1].begin() + 12);
    require(extended != original && extended->program == expected && original->program == programs[0], 0x43);
    load(handles[0], slots[0]);
    require(select(handles[0], slots[0])->program == programs[0], 0x44);
    auto declaration_before = g_vs.at(handles[0]);
    auto selection_before = select(handles[0], slots[0]);
    auto replacement = std::make_shared<gpu::VertexShader>(*declaration_before);
    replacement->inputs[0].type ^= 1;
    g_vs[handles[0]] = replacement;
    auto selection_after = select(handles[0], slots[0]);
    require(selection_after != selection_before && selection_after->program == programs[0] &&
            selection_after->inputs[0].type == replacement->inputs[0].type, 0x45);
    g_vs[handles[0]] = declaration_before;
    require(select(handles[0], UINT32_MAX)->program.empty(), 0x46);
    std::memcpy(g_program, saved_program, sizeof(g_program));
    g_program_selections.fill({});
    g_selected = saved_selected; g_state = std::move(saved_state);
    std::fprintf(stderr, "[SHADER-CONTRACT-PASS] guest-sized slots preserve complete programs across selection\n");
}

// Exercise direct guest writes between the two vertex paths, including the
// other registers that share the viewport's eight-register recorder block.
static void NativeVertexConstantContract() {
    auto require = [](bool okay, unsigned detail) {
        if (!okay) ngb_stop("native vertex constant sync failed", detail);
    };
    const auto saved = g_state;
    const uint32_t saved_changes = native_mesh_changed;
    auto* guest = static_cast<uint8_t*>(HostPtr(kVsConstants, sizeof(g_state.vsc)));
    decltype(g_state.vsc) saved_guest;
    std::memcpy(saved_guest.data(), guest, sizeof(saved_guest));
    g_state = gpu::State{};
    g_state.vs_handle = 0x142;
    native_mesh_changed = ~0u;
    for (unsigned i = 0; i < sizeof(g_state.vsc) / 4; ++i) W32(kVsConstants + 4 * i, 0x3f000000u + i);
    SyncDrawConstants();
    require(g_state.constants_revision && g_state.changed_constant_blocks == (1u << 7), 1);
    auto rev = g_state.constants_revision;
    native_mesh_changed = 0;
    W32(kVsConstants + 60 * 16, 0x80000000u);
    SyncDrawConstants();
    require(g_state.constants_revision == rev, 2);
    auto check_program = [&] {
        decltype(g_state.vsc) expected;
        std::memcpy(expected.data(), guest, sizeof(expected));
        ViewportConstants(expected[58], expected[59]);
        require(!std::memcmp(expected.data(), g_state.vsc.data(), sizeof(expected)), 3);
    };
    g_state.vs_handle = 1;
    SyncDrawConstants();
    check_program();
    W32(kVsConstants + 191 * 16 + 12, 0x7fc12345u);
    SyncDrawConstants();
    require(g_state.changed_constant_blocks == (1u << 23), 4);
    check_program();
    g_state.vs_handle = 0x142;
    g_state.viewport.w = 320;
    MarkDrawState(Groups::PixelConstantsAndTargets);
    SyncDrawConstants();
    require(g_state.vsc[58][0] == 160 && g_state.changed_constant_blocks == (1u << 7), 5);
    W32(kVsConstants + 57 * 16, 0x7fc01234u);
    g_state.vs_handle = 1;
    SyncDrawConstants();
    check_program();
    require(g_state.changed_constant_blocks == (1u << 7), 6);
    std::memcpy(guest, saved_guest.data(), sizeof(saved_guest));
    g_state = saved;
    native_mesh_changed = saved_changes;
    std::fprintf(stderr, "[VERTEX-CONSTANT-PASS] fixed, programmable, viewport and inline writes\n");
}
