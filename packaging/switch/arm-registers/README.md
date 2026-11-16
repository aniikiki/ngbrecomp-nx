This private Switch build uses a different calling convention inside fourteen
frequently executed guest translation units. It requires the normal Direct3D
Switch build and the same devkitA64 compiler. Run
`bash packaging/switch/arm-registers/build.sh` from the checkout. The baseline
NRO remains available; the candidate is written under
`build/switch-runtime/history/0.51.0-rc1/`. Generated sources, objects,
executables and disc data must stay in the ignored build directory.

The guest keeps eax/ecx/edx/esp/ebx/esi/edi in x19–x25. x26 and x27 carry RAM
and the page table; x28 points to the saved register file. Public symbols have
the ordinary AArch64 ABI. Internal direct branches target private symbols; an
indirect call uses the public convention. The special entry checkpoint keeps
the same history, polling tickets and startup events as runtime.c. Foreign calls
which can see or change the guest CPU synchronize its values, including before
an interrupt can run. The generated ARM uses the production compiler flags
plus -ffixed-x28, -fno-ipa-ra and -fno-optimize-sibling-calls. See
[the compiler reproducer](../perf/verify-register-codegen.py).

After establishing the offline `perf/replay.sh baseline`, build
`host-check.py --rigid-clip` inside the host image to link the freshly packaged Switch
objects with host services. Use that runner for the retail combat and Chapter 1
controller replays. The host measures CPU time; it cannot validate Switch FPS.

0.51 also compiles the isolated Vulkan object with NGB_RIGID_CLIP. For the three
unskinned fixed-function FVF formats it can reject a triangle submission only
when one common side clip plane excludes every position in the assembled
stream, with a floating-point margin. This happens on the render thread.
Original visibility reports and optional continuous glow use the ordinary path.
The renderer emits one aggregate count per 120 presents to the existing log.
