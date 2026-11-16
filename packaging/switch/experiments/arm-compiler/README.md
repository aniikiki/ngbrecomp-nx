# Offline AArch64 compiler comparison

Run `python3 packaging/switch/experiments/arm-compiler/cross.py` from the repository root on a host with Clang's AArch64 ELF backend. The compiler uses the libnx/newlib headers already present in the Switch build container and the current private disc-derived source tree. Its output is device machine code, not a macOS executable.

Inside the ARM Linux replay container, run `python3 packaging/switch/experiments/arm-compiler/link.py`, then run the normal combat replay with `core-perf/compiler-pair/replay`. Both arms use the public register ABI. This comparison isolates the compiler; a win against public GCC would still have to be compared against the packaged private-register build. Frame 1920, gameplay integrity, comparable work, and a repeated serial timing run are necessary before considering a Switch package.
