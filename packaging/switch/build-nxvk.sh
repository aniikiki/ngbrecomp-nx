#!/usr/bin/env bash
# Build the pinned Switch Vulkan driver and a small set of validation programs.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
nxvk=${NXVK_DIR:-$(dirname "$root")/nxvk}
revision=c3abea1efde44027b7e3e20b48eb55beeecd5ab4
image=ngb-switch-nxvk:dev
if [[ ! -d "$nxvk" ]]; then
    git init "$nxvk"
    git -C "$nxvk" remote add origin https://github.com/PalindromicBreadLoaf/nxvk.git
    git -C "$nxvk" fetch --depth 1 origin "$revision"
    git -C "$nxvk" checkout --detach FETCH_HEAD
fi
if [[ $(git -C "$nxvk" rev-parse HEAD) != "$revision" ]]; then
    echo "NXVK checkout must be at $revision; existing checkout left untouched." >&2
    exit 1
fi
docker build -t "$image" -f "$root/packaging/switch/Dockerfile.nxvk" "$nxvk/switch/docker"
docker run --rm --cpus=4 --memory=6g \
    -e NGB_BUILD_JOBS="${NGB_BUILD_JOBS:-2}" -e CARGO_BUILD_JOBS=2 \
    -v "$nxvk:/work" -v "$root:/ngb" -w /work "$image" \
    bash /ngb/packaging/switch/build-nxvk-in-container.sh
mkdir -p "$root/build/switch-probe"
git -C "$nxvk" rev-parse HEAD > "$root/build/switch-probe/nxvk-revision.txt"
docker image inspect "$image" --format '{{.Id}}' > "$root/build/switch-probe/nxvk-image.txt"
