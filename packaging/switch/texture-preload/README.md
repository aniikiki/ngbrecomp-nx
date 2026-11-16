# Switch texture preload (0.56.1)

This option builds on the 0.56.0 opening pipeline warmup. Run the existing
package-retained.py with --hardware-test --pipe-attribution --opening-warm
--texture-preload in the nxvk build image. The build scans local retail AFS
archives for static 2D texture descriptors in KMD/XPR0 members. The NRO adds
offsets, sizes and formats, not pixel data. The archive names do not select
specific levels or character IDs.

Successful game reads from an indexed archive (including partial-disc catalog
reads) supply the pixel bytes. A partial texture must be complete before it
is eligible. No extra game-file reads, speculative guest-memory writes, or
Vulkan calls on the file thread are required. At title scanout the prepared
title backend uploads in small groups; the same device is adopted at the first
scene. During play, the render thread prepares a bounded number of items at a
present or during an idle interval. Time budgets are checked between items,
not hard deadlines on an individual driver call.

On first draw, the live content signature, dimensions, mip count and format
must agree before an image can replace an ordinary upload. Cache misses still
draw through the original path. Render targets, palettes, dynamic content not
represented by the index, and oversized textures are not speculatively
uploaded. The working queue and prepared image cache have separate budgets.
A texture may miss because its data arrived late, its entry was evicted, or
its layout was not supported.

Texture preload defaults on. To turn off only texture preload, create
/switch/ngb-runtime/disable-texture-preload.flag and restart. Remove the flag
and restart to turn it back on. Pipeline warmup has its own unchanged flag.

Run compare.sh in the headless host image, then run report.py with the replay
output directory. [TEX_PRELOAD] reports cumulative prepared images, title
preparations, first-use hits and eligible misses; gpu_bytes covers unconsumed
prepared images only. [TEX_FIRST_USE] measures the foreground creation/upload
recording path; it is not a GPU execution time or complete frame time. Only a
Switch run at matched clocks can establish an improvement in gameplay stalls.
