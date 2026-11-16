set -eu
d=build/switch-runtime/core-perf/opening-setup
mkdir -p "$d/hdd"
export NGB_TEST_IDLE_SCENE=benchmark LP_NUM_THREADS=4 VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.aarch64.json
export NGB_DIRECT_SPIRV=/work/build/switch-runtime/direct/cache/spirv.bin XDG_CACHE_HOME=/work/build/switch-runtime/direct/mesa-cache
"$d/replay" --start-button build/switch-runtime/romfs "$d/hdd" > "$d/$1.log" 2>&1 || :
grep -Fq '[RESULT] status=1 reason=verified 120 original demo frames' "$d/$1.log"
