# Mission and main menu attribution, 0.56.23

These traces concern the selection screens, not gameplay or the chapter loading icon.
The Linux/AArch64 replay drove the retail main menu, the unlocked Mission list, and its
difficulty overlay with scripted controller input. It used llvmpipe, discarded console
output, and had no Horizon display thread. A frontbuffer swap is not a displayed frame.

## Guest memory and the wait loop

Both sides of the final comparison used the 47 guest objects checked by SHA-256 against
the Horizon package's linked-inputs.txt, with host services and separate temporary saves.
The counter incremented on every scalar fallback, and sampled the address and last
guest checkpoint once per 257 calls. In the control, the same pair (guest checkpoint
003CAB40, contiguous address 86674000) accounted for approximately 99%, 98%, and 98%
of the fallback samples. 003CAB40 is the backward branch inside D3D_BlockOnTime:
it repeatedly reads the completion value until the game's comparison succeeds.

| Screen | Baseline swaps / seconds | Fallbacks / swap | Experimental swaps / seconds | Fallbacks / swap |
| --- | ---: | ---: | ---: | ---: |
| Main | 128 / 2.1333 | 383418 | 128 / 2.1343 | 12500 |
| Mission | 174 / 2.9000 | 321899 | 173 / 2.8835 | 14150 |
| Difficulty | 96 / 1.6000 | 310841 | 95 / 1.5842 | 14071 |

Treatment: request a 150-microsecond sleep at the periodic spin hook, only for this
loop in the three observation windows; still run the real hook and recheck the original
condition. Both variants reached the same screens and maintained ~60 guest swaps/s.
This isolates busy polling in a host run already paced to 60. It does not measure
uncapped throughput or show whether the console has the same scheduling headroom.
No delay has been added to the player.

## Menu renderer and readback

The direct Vulkan scene flag stayed zero in all three final windows. Main recorded
one GL readback per swap, Mission and Difficulty three. With the retained objects,
readback calls (including implicit waits) cost 4.05, 4.66 and 2.26 ms per guest swap
respectively in the baseline. On an earlier real console trace (0.55.1 archive,
boot.previous.log), main menu logged 92 swaps / 3031 ms and 506 ms for 92 readbacks;
this is not a current console baseline.

Two further host controls used the earlier replay ABI. First, disabling the GL menu
overlay preserved navigation and removed readbacks, but FIFO processing time **rose**
from 5.81 to 8.87 ms/swap (main) and 6.83 to 9.44 ms/swap (Mission). Second, a
diagnostic glFinish immediately before each readback put 500.12 of 506.27 ms (main),
742.47 of 752.01 ms (Mission), and 343.79 of 348.96 ms (Difficulty) into the finish
call. These numbers isolate pending GL work on the software driver; the finish is
an intervention, not a measurement of Switch GPU time or pure memory bandwidth.

## Next discriminating measurement

The opt-in player trace now counts guest flips, published snapshots, and frames
displayed over the instrumented Mission loops. Compare totals over many loops;
identical images may legitimately be suppressed. D rows separate display acquire,
scaling/overlay, and framebufferEnd. PC/LR samples require mission-pc.flag, and
the sparse GL finish/read split requires mission-gl-sync.flag, both in addition
to mission-perf.flag. Capture the plain trace for baseline frame pacing before
enabling intrusive probes. No generic tracing was added to the main menu.

## Switch 0.56.23: cold Mission vs. Mission after attract mode

Matched state 1 only: the cold capture has 555 iterations, median 33.325 ms,
1,661 GL reads and zero Vulkan presents. The post-demo capture has 1,105
iterations, median 16.662 ms, zero GL reads and 1,105 Vulkan presents.
This route change persists beyond the menu entry transition.

The route latch is ngb_scene_active in runtime/scene/bridge.c. Inline primitive
6 does not trigger it; ARRAY_ELEMENT16/32, DRAW_ARRAYS, or a nonzero BEGIN of
another primitive does. The switch flushes/closes the boot menu renderer,
changes the polling mask and enables contiguous guest banks. On a subsequent
HLE call the Direct3D backend starts, adopting the title's prewarmed device if
available. Preparing that device alone does not change the route. Returning
to the title does not clear the latch; scene shutdown does. The published NRO
also contains the primitive-6 bypass at text offset 0x50d220 and menu GPU close
at 0x50d230. The logs don't identify which particular demo packet first set
the latch, nor how much of the speedup belongs to polling versus rendering.

A focused fix should reuse the existing handoff on a confirmed interactive-menu
frame boundary, before the next frame's draw hooks. Do not simply allow every
triangle strip to trigger the latch: boot and movies share the early presenter.
Validate cold main/Mission images, difficulty navigation, presentation counts
and startup/movie/subtitle regressions against the existing post-demo route.
