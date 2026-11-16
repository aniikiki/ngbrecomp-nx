#!/usr/bin/env bash
set -euo pipefail
cd /work
# Upstream invokes Ninja from several scripts; keep all of them within the
# memory budget of an 8 GiB Docker VM, including its native shader compiler.
cat > /usr/local/bin/ninja <<'WRAPPER'
#!/usr/bin/env bash
exec /usr/bin/ninja -j"${NGB_BUILD_JOBS:-2}" "$@"
WRAPPER
chmod +x /usr/local/bin/ninja
export PATH="/usr/local/bin:/work/switch/build/native-tools/bin:$PATH"
make CONTAINER=
bash switch/smoke/shaders/gen-shaders.sh
python3 /ngb/packaging/switch/prepare-nxvk-probes.py /work
probe_build=/ngb/build/switch-probe/nxvk-sources/build-nro.sh
for app in nvk_smoke nvk_tri nvk_textures nvk_vi_swapchain; do
    VERSION=0.1.1 bash "$probe_build" "$app"
done
TITLE="NGB Vulkan Caps" VERSION=0.1.1 bash "$probe_build" ngb_vk_caps
mkdir -p /ngb/build/switch-probe/nxvk
for app in nvk_smoke nvk_tri nvk_textures nvk_vi_swapchain ngb_vk_caps; do
    cp "/ngb/build/switch-probe/nxvk-sources/out/$app.nro" /ngb/build/switch-probe/nxvk/
done
